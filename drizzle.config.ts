import type { Config } from 'drizzle-kit';

export default {
  schema:    './src/db/schema.ts',
  out:       './drizzle/migrations',
  dialect:   'sqlite',
  dbCredentials: {
    url: './data/neuro_learn.db',
  },
} satisfies Config;