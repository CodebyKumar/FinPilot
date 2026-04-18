'use client';

import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function ForgotPasswordPage() {
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
          Reset Password
        </h1>
        <p style={{
          color: 'var(--muted)',
          textAlign: 'center',
          marginBottom: '2rem',
          fontSize: '0.95rem',
        }}>
          Enter your email to receive a password reset link
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <Input
            label="Email"
            type="email"
            placeholder="you@example.com"
            containerStyle={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
          />

          <Button variant="primary" style={{ width: '100%' }}>
            Send Reset Link
          </Button>

          <Link href="/login" style={{
            textAlign: 'center',
            color: 'var(--indigo)',
            textDecoration: 'none',
            fontSize: '0.9rem',
          }}>
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
}
