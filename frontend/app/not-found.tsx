import Link from 'next/link';

export default function NotFound() {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      flexDirection: 'column',
      gap: '1.5rem',
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: '4rem', fontFamily: 'Syne', fontWeight: 800, marginBottom: '0.5rem', color: 'var(--amber)' }}>
          404
        </h1>
        <h2 style={{ fontSize: '1.5rem', fontFamily: 'Syne', marginBottom: '0.5rem' }}>
          Page not found
        </h2>
        <p style={{ color: 'var(--muted)', marginBottom: '1.5rem' }}>
          The page you&apos;re looking for doesn&apos;t exist.
        </p>
      </div>
      <Link 
        href="/"
        style={{
          padding: '0.75rem 1.5rem',
          background: 'var(--indigo)',
          color: 'white',
          borderRadius: '0.5rem',
          textDecoration: 'none',
          fontWeight: 600,
        }}
      >
        Go Home
      </Link>
    </div>
  );
}
