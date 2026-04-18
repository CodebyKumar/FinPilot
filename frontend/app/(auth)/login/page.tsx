'use client';

import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function LoginPage() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      background: 'var(--bg)',
      padding: '2rem',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        background: 'var(--bg2)',
        border: '1px solid var(--border)',
        borderRadius: '1rem',
        padding: '2rem',
      }}>
        <h1 style={{
          fontSize: '1.75rem',
          fontFamily: 'Syne',
          fontWeight: 700,
          marginBottom: '0.5rem',
          textAlign: 'center',
        }}>
          Welcome Back
        </h1>
        <p style={{
          color: 'var(--muted)',
          textAlign: 'center',
          marginBottom: '2rem',
          fontSize: '0.95rem',
        }}>
          Sign in to your FinPilot account
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="Email"
            type="email"
            placeholder="you@example.com"
            containerStyle={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            containerStyle={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
            <input type="checkbox" />
            <span>Remember me</span>
          </label>

          <Button variant="primary" style={{ width: '100%' }}>
            Sign In
          </Button>

          <Link href="/forgot-password" style={{
            textAlign: 'center',
            color: 'var(--indigo)',
            textDecoration: 'none',
            fontSize: '0.9rem',
          }}>
            Forgot password?
          </Link>

          <div style={{
            textAlign: 'center',
            fontSize: '0.9rem',
            color: 'var(--muted)',
          }}>
            Don't have an account?{' '}
            <Link href="/register" style={{
              color: 'var(--indigo)',
              textDecoration: 'none',
              fontWeight: 600,
            }}>
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
