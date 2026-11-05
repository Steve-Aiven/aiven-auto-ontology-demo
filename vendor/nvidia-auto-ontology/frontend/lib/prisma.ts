// SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
// All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { PrismaClient } from '@/generated/prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

function buildConnectionString(): string {
	const host = process.env.POSTGRES_HOST ?? 'localhost';
	const port = process.env.POSTGRES_PORT ?? '5432';
	const user = process.env.POSTGRES_USER;
	const password = process.env.POSTGRES_PASSWORD;
	const database = process.env.POSTGRES_DATABASE;
	// Aiven (and most managed Postgres) reject non-SSL; without sslmode the
	// pg driver error surfaces as Prisma P1010 DatabaseAccessDenied.
	const sslmode = process.env.POSTGRES_SSLMODE ?? 'require';

	if (!user || !password || !database) {
		// `next build` evaluates the module graph (e.g. the Better Auth route)
		// but never opens a DB connection — all routes are dynamic. Return a
		// non-connecting placeholder so the build doesn't require Postgres env;
		// real values are still required at runtime.
		if (process.env.NEXT_PHASE === 'phase-production-build') {
			return 'postgresql://build:build@localhost:5432/build';
		}
		throw new Error(
			'POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DATABASE must be set in the root .env file',
		);
	}

	const u = encodeURIComponent(user);
	const p = encodeURIComponent(password);
	// Node `pg` currently aliases require/prefer/verify-ca to verify-full, which
	// fails against Aiven's chain ("self-signed certificate in certificate chain").
	// uselibpqcompat restores libpq semantics so require means encrypt-only.
	return `postgresql://${u}:${p}@${host}:${port}/${database}?sslmode=${encodeURIComponent(sslmode)}&uselibpqcompat=true`;
}

function createPrismaClient(): PrismaClient {
	const adapter = new PrismaPg({ connectionString: buildConnectionString() });
	return new PrismaClient({ adapter });
}

/** Lazy singleton — only connects when first accessed at runtime, not at import/build time. */
export function getPrisma(): PrismaClient {
	const client = globalForPrisma.prisma ?? createPrismaClient();
	if (process.env.NODE_ENV !== 'production') {
		globalForPrisma.prisma = client;
	}
	return client;
}
