'use client';

import Link from 'next/link';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export default function RegisterPage() {
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
        maxWidth: '500px',
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
          Create Account
        </h1>
        <p style={{
          color: 'var(--muted)',
          textAlign: 'center',
          marginBottom: '2rem',
          fontSize: '0.95rem',
        }}>
          Join thousands of SMBs using FinPilot
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <Input placeholder="First Name" />
            <Input placeholder="Last Name" />
          </div>

          <Input
            type="email"
            placeholder="you@example.com"
            label="Email"
          />

          <Input
            type="text"
            placeholder="Your Business Name"
            label="Business Name"
          />

          <Input
            type="password"
            placeholder="Create a strong password"
            label="Password"
          />

          <Input
            type="password"
            placeholder="Confirm password"
            label="Confirm Password"
          />

          <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.85rem' }}>
            <input type="checkbox" style={{ marginTop: '0.25rem' }} />
            <span>
              I agree to the{' '}
              <Link href="#" style={{ color: 'var(--indigo)', textDecoration: 'none' }}>
                Terms of Service
              </Link>
              {' '}and{' '}
              <Link href="#" style={{ color: 'var(--indigo)', textDecoration: 'none' }}>
                Privacy Policy
              </Link>
            </span>
          </label>

          <Button variant="primary" style={{ width: '100%' }}>
            Create Account
          </Button>

          <div style={{
            textAlign: 'center',
            fontSize: '0.9rem',
            color: 'var(--muted)',
          }}>
            Already have an account?{' '}
            <Link href="/login" style={{
              color: 'var(--indigo)',
              textDecoration: 'none',
              fontWeight: 600,
            }}>
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
