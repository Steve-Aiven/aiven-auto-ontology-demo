// SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
// All rights reserved.
// SPDX-License-Identifier: Apache-2.0

// Decorator-style guards for API route handlers. Every API route export is
// exactly one of these two wrappers — there is no third "authenticated but no
// permission" tier and no bare handler:
//
//   export const GET = withPublic(async (req) => { ... });
//   export const POST = withPermission({ acronym: ['create'] })(async (req, { user }) => { ... });
//
// `withPermission` resolves the caller via resolveUser() — a Better Auth session
// cookie (browser) or a verified SSO bearer token (service callers such as AI-Q)
// — checks the permission with userCan(), and injects the resolved `user` into
// the handler context. Dynamic-route params are preserved, so handlers still
// receive `{ params, user }`.

import { NextResponse } from 'next/server';
import { resolveUser, type ResolvedUser } from '@/auth/resolve-user';
import { userCan, type PermissionRequest } from '@/auth/permissions';

// The context Next passes to a route handler. Next requires *every* route
// handler — even non-dynamic ones — to accept a context with `params`; static
// routes just resolve to an empty params object. Default the generic to this
// wide shape so both `withPermission({...})(fn)` (static) and
// `withPermission<{ params: Promise<{ id: string }> }>({...})(fn)` (dynamic)
// satisfy Next's generated route types at build time.
// A catch-all segment (`[...all]`) resolves to a string[], so the value type has
// to admit both or the auth catch-all cannot be wrapped.
type RouteContext = { params: Promise<Record<string, string | string[]>> };

type AuthedHandler<C extends RouteContext> = (
	req: Request,
	ctx: C & { user: ResolvedUser },
) => Response | Promise<Response>;

type PublicHandler<C extends RouteContext> = (req: Request, ctx: C) => Response | Promise<Response>;

const unauthorized = () => NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
const forbidden = () => NextResponse.json({ error: 'Forbidden' }, { status: 403 });

/**
 * Mark a route as deliberately unauthenticated. Wraps so the exported handler
 * always declares a required Next `RouteContext` second argument — a bare
 * `(req) => ...` pass-through types the context as optional/`undefined`, which
 * fails Next 16's generated ParamCheck at `next build`.
 */
export function withPublic<C extends RouteContext = RouteContext>(
	handler: PublicHandler<C>,
): (req: Request, ctx: C) => Promise<Response> {
	return async (req: Request, ctx: C): Promise<Response> => handler(req, ctx);
}

/**
 * Require an authenticated caller who holds the given permission(s). Injects the
 * resolved `user` (id + role) into the handler. 401 when the caller can't be
 * resolved, 403 when the permission is missing.
 *
 * Context must be required (no default `= {}`): a defaulted second parameter is
 * typed as `C | undefined` and fails Next 16 route ParamCheck the same way.
 */
export function withPermission<C extends RouteContext = RouteContext>(
	permissions: PermissionRequest,
): (handler: AuthedHandler<C>) => (req: Request, ctx: C) => Promise<Response> {
	return (handler: AuthedHandler<C>) =>
		async (req: Request, ctx: C): Promise<Response> => {
			const user = await resolveUser();
			if (!user) return unauthorized();
			if (!userCan(user, permissions)) return forbidden();
			return handler(req, { ...ctx, user });
		};
}
