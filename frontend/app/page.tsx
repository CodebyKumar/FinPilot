import Link from 'next/link';

export default function Home() {
  return (
    <main style={{ background: 'var(--bg)', color: 'var(--text)', minHeight: '100vh', padding: '2rem' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Hero Banner */}
        <section style={{ marginBottom: '4rem', textAlign: 'center', paddingTop: '4rem' }}>
          <h1 style={{ fontSize: '3.5rem', fontFamily: 'Syne', fontWeight: 800, marginBottom: '1rem', lineHeight: 1.2 }}>
            Your AI CFO Assistant
          </h1>
          <p style={{ fontSize: '1.25rem', color: 'var(--muted)', marginBottom: '2rem', maxWidth: '600px', margin: '0 auto 2rem' }}>
            FinPilot helps SMBs manage finances, file taxes, and optimize compliance with intelligent automation.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <Link 
              href="/login"
              style={{
                padding: '0.75rem 1.5rem',
                background: 'var(--indigo)',
                color: 'white',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              Login
            </Link>
            <Link 
              href="/register"
              style={{
                padding: '0.75rem 1.5rem',
                background: 'var(--bg3)',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                fontWeight: 600,
              }}
            >
              Get Started
            </Link>
          </div>
        </section>

        {/* Features */}
        <section style={{ marginBottom: '4rem' }}>
          <h2 style={{ fontSize: '2rem', fontFamily: 'Syne', fontWeight: 700, marginBottom: '2rem', textAlign: 'center' }}>
            Why Choose FinPilot?
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
            {[
              { title: '📊 Intelligent Bookkeeping', description: 'Auto-parse statements and invoices with AI-powered categorization' },
              { title: '📋 Smart Report Filing', description: 'Generate and validate tax reports with zero compliance errors' },
              { title: '💡 AI Assistant', description: 'Chat with your personal finance advisor for tax strategies' },
              { title: '📅 Deadline Tracking', description: 'Never miss a filing deadline with intelligent reminders' },
              { title: '🔒 Secure & Private', description: 'Bank-grade security for all your financial data' },
              { title: '⚡ Real-time Insights', description: 'Monitor profit, expenses, and tax liability instantly' },
            ].map((feature, idx) => (
              <div
                key={idx}
                style={{
                  padding: '2rem',
                  background: 'var(--bg2)',
                  border: '1px solid var(--border)',
                  borderRadius: '0.75rem',
                }}
              >
                <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>{feature.title}</h3>
                <p style={{ color: 'var(--muted)', fontSize: '0.95rem' }}>{feature.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section style={{ textAlign: 'center', padding: '3rem 2rem', background: 'var(--bg2)', borderRadius: '1rem', border: '1px solid var(--border)' }}>
          <h2 style={{ fontSize: '2rem', fontFamily: 'Syne', marginBottom: '1rem' }}>Ready to simplify your finances?</h2>
          <p style={{ color: 'var(--muted)', marginBottom: '2rem' }}>Join SMBs who trust FinPilot for financial management.</p>
          <Link 
            href="/register"
            style={{
              display: 'inline-block',
              padding: '0.875rem 2rem',
              background: 'var(--emerald)',
              color: 'white',
              borderRadius: '0.5rem',
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            Start Free Trial
          </Link>
        </section>
      </div>
    </main>
  );
}
