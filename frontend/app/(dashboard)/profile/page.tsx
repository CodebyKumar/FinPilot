'use client';

import { useEffect, useState } from 'react';
import { PageShell } from '@/components/layout/page-shell';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api-client';

interface ProfileFormState {
  fullName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  pan: string;
  aadhaar: string;
  businessName: string;
  entityType: string;
  gstNumber: string;
  accountHolderName: string;
  accountNumber: string;
  ifscCode: string;
  bankName: string;
  streetAddress: string;
  city: string;
  state: string;
  pinCode: string;
}

interface ProfileSchemaPayload {
  personal_info: Record<string, any>;
  business_info: Record<string, any>;
  income_sources: Array<Record<string, any> | string>;
  bank_accounts: Array<Record<string, any> | string>;
  tax_preferences: Record<string, any>;
}

interface ProfileIdentifiers {
  userId: string | null;
  backendUserId: string | null;
}

const EMPTY_FORM: ProfileFormState = {
  fullName: '',
  email: '',
  phone: '',
  dateOfBirth: '',
  pan: '',
  aadhaar: '',
  businessName: '',
  entityType: '',
  gstNumber: '',
  accountHolderName: '',
  accountNumber: '',
  ifscCode: '',
  bankName: '',
  streetAddress: '',
  city: '',
  state: '',
  pinCode: '',
};

export default function ProfilePage() {
  const userId = 'default';

  const [form, setForm] = useState<ProfileFormState>(EMPTY_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<'success' | 'error' | null>(null);
  const [hasExistingProfile, setHasExistingProfile] = useState(false);
  const [loadedProfile, setLoadedProfile] = useState<ProfileSchemaPayload | null>(null);
  const [profileIdentifiers, setProfileIdentifiers] = useState<ProfileIdentifiers>({
    userId: null,
    backendUserId: null,
  });

  const getErrorMessage = (error: unknown, fallback: string) => {
    const maybeAxios = error as {
      response?: {
        data?: {
          detail?: string;
        };
      };
      message?: string;
    };
    return maybeAxios?.response?.data?.detail || maybeAxios?.message || fallback;
  };

  const updateField = (key: keyof ProfileFormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  useEffect(() => {
    let isMounted = true;

    const loadProfile = async () => {
      try {
        setIsLoading(true);
        const response = await apiClient.getProfile(userId);
        const payload = response?.data || response;
        const data = payload?.data || payload;
        const profile = data?.profile ?? {};
        const user = data?.user ?? {};
        const profileExists = Object.keys(profile).length > 0;
        const personal = profile?.personal_info ?? {};
        const business = profile?.business_info ?? {};
        const bank = Array.isArray(profile?.bank_accounts) ? profile.bank_accounts[0] ?? {} : {};
        const address = personal?.address ?? {};

        setLoadedProfile({
          personal_info: typeof personal === 'object' && personal !== null ? personal : {},
          business_info: typeof business === 'object' && business !== null ? business : {},
          income_sources: Array.isArray(profile?.income_sources) ? profile.income_sources : [],
          bank_accounts: Array.isArray(profile?.bank_accounts) ? profile.bank_accounts : [],
          tax_preferences:
            typeof profile?.tax_preferences === 'object' && profile.tax_preferences !== null
              ? profile.tax_preferences
              : {},
        });

        if (!isMounted) return;

        setHasExistingProfile(profileExists);
        setProfileIdentifiers({
          userId: profileExists ? (profile?.user_id ?? user?.external_user_id ?? userId) : null,
          backendUserId: profileExists ? (user?._id ?? null) : null,
        });
        setForm({
          fullName: personal?.full_name ?? '',
          email: personal?.email ?? '',
          phone: personal?.phone ?? '',
          dateOfBirth: personal?.dob ?? '',
          pan: personal?.pan ?? '',
          aadhaar: personal?.aadhaar ?? '',
          businessName: business?.business_name ?? '',
          entityType: business?.entity_type ?? '',
          gstNumber: business?.gst_number ?? '',
          accountHolderName: bank?.account_holder_name ?? '',
          accountNumber: bank?.account_number ?? '',
          ifscCode: bank?.ifsc ?? '',
          bankName: bank?.bank_name ?? '',
          streetAddress: address?.street ?? '',
          city: address?.city ?? '',
          state: address?.state ?? '',
          pinCode: address?.pin_code ?? '',
        });
      } catch (error) {
        if (!isMounted) return;
        const message = getErrorMessage(error, 'Unable to load profile');
        setStatusType('error');
        setStatusMessage(message);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadProfile();

    return () => {
      isMounted = false;
    };
  }, [userId]);

  const handleSaveProfile = async () => {
    try {
      setIsSaving(true);
      setStatusMessage(null);
      setStatusType(null);

      const existingPersonal = loadedProfile?.personal_info ?? {};
      const existingBusiness = loadedProfile?.business_info ?? {};
      const existingBankAccounts = loadedProfile?.bank_accounts ?? [];
      const firstBankAccountRaw =
        existingBankAccounts.length > 0 &&
        typeof existingBankAccounts[0] === 'object' &&
        existingBankAccounts[0] !== null
          ? (existingBankAccounts[0] as Record<string, any>)
          : {};

      const personalInfo: Record<string, any> = {
        ...existingPersonal,
        full_name: form.fullName.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        dob: form.dateOfBirth,
        address: {
          ...(typeof existingPersonal.address === 'object' && existingPersonal.address !== null
            ? existingPersonal.address
            : {}),
          street: form.streetAddress.trim(),
          city: form.city.trim(),
          state: form.state.trim(),
          pin_code: form.pinCode.trim(),
        },
      };

      // Avoid re-saving masked values returned by backend (`***`)
      if (form.pan.trim() && !form.pan.includes('*')) {
        personalInfo.pan = form.pan.trim().toUpperCase();
      }
      if (form.aadhaar.trim() && !form.aadhaar.includes('*')) {
        personalInfo.aadhaar = form.aadhaar.trim();
      }

      const payload: ProfileSchemaPayload = {
        personal_info: personalInfo,
        business_info: {
          ...existingBusiness,
          business_name: form.businessName.trim(),
          entity_type: form.entityType.trim(),
          gst_number: form.gstNumber.trim().toUpperCase(),
        },
        bank_accounts: [
          {
            ...firstBankAccountRaw,
            account_holder_name: form.accountHolderName.trim(),
            account_number: form.accountNumber.trim(),
            ifsc: form.ifscCode.trim().toUpperCase(),
            bank_name: form.bankName.trim(),
          },
        ],
        income_sources: loadedProfile?.income_sources ?? [],
        tax_preferences: loadedProfile?.tax_preferences ?? {},
      };

      if (!hasExistingProfile) {
        if (!payload.personal_info.full_name || !payload.personal_info.phone || !payload.personal_info.dob) {
          throw new Error('Full Name, Phone, and Date of Birth are required to create profile.');
        }
        if (!personalInfo.pan) {
          throw new Error('PAN is required to create profile.');
        }
        if (!payload.business_info.business_name || !payload.business_info.entity_type) {
          throw new Error('Business Name and Entity Type are required to create profile.');
        }

        const createResponse = await apiClient.createProfile({
          user_id: userId,
          ...payload,
        });
        setHasExistingProfile(true);
        setProfileIdentifiers({
          userId: createResponse?.data?.user_id ?? userId,
          backendUserId: createResponse?.data?.backend_user_id ?? null,
        });
      } else {
        await apiClient.updateProfile(userId, payload);
        setProfileIdentifiers((prev) => ({
          userId: prev.userId ?? userId,
          backendUserId: prev.backendUserId,
        }));
      }

      setLoadedProfile(payload);

      setStatusType('success');
      setStatusMessage(hasExistingProfile ? 'Profile updated successfully.' : 'Profile created successfully.');
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to save profile');
      setStatusType('error');
      setStatusMessage(message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <PageShell
      title="My Profile"
      subtitle="Manage your personal and business information"
    >
      {statusMessage && statusType && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: `1px solid ${statusType === 'success' ? 'var(--emerald)' : 'var(--rose)'}`,
            color: statusType === 'success' ? 'var(--emerald)' : 'var(--rose)',
            background: statusType === 'success' ? 'var(--card-glow-emerald)' : 'rgba(244, 63, 94, 0.08)',
          }}
        >
          {statusMessage}
        </div>
      )}

      {hasExistingProfile && profileIdentifiers.userId && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '0.75rem 1rem',
            borderRadius: '0.5rem',
            border: '1px solid var(--border)',
            background: 'var(--bg2)',
            color: 'var(--text)',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '0.35rem' }}>Profile ID Details</div>
          <div style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>
            App User ID: <span style={{ color: 'var(--text)', fontWeight: 600 }}>{profileIdentifiers.userId}</span>
          </div>
          {profileIdentifiers.backendUserId && (
            <div style={{ fontSize: '0.9rem', color: 'var(--muted)', marginTop: '0.2rem' }}>
              Mongo User ID: <span style={{ color: 'var(--text)', fontWeight: 600 }}>{profileIdentifiers.backendUserId}</span>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Personal Information */}
        <Card title="Personal Information">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Input
              label="Full Name"
              placeholder="Enter your full name"
              value={form.fullName}
              onChange={(e) => updateField('fullName', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Email"
              type="email"
              placeholder="Enter your email"
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Phone"
              placeholder="Enter your phone number"
              value={form.phone}
              onChange={(e) => updateField('phone', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Date of Birth"
              type="date"
              value={form.dateOfBirth}
              onChange={(e) => updateField('dateOfBirth', e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
        </Card>

        {/* Tax Information */}
        <Card title="Tax Information">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Input
              label="PAN"
              placeholder="Enter your PAN"
              value={form.pan}
              onChange={(e) => updateField('pan', e.target.value.toUpperCase())}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Aadhaar (masked)"
              placeholder="Enter Aadhaar"
              value={form.aadhaar}
              onChange={(e) => updateField('aadhaar', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Business Name"
              placeholder="Enter business name"
              value={form.businessName}
              onChange={(e) => updateField('businessName', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Entity Type"
              placeholder="e.g. Proprietorship / Pvt Ltd / LLP"
              value={form.entityType}
              onChange={(e) => updateField('entityType', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="GST Number"
              placeholder="Enter GST number"
              value={form.gstNumber}
              onChange={(e) => updateField('gstNumber', e.target.value.toUpperCase())}
              disabled={isLoading || isSaving}
            />
          </div>
        </Card>

        {/* Bank Details */}
        <Card title="Bank Details">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Input
              label="Account Holder Name"
              value={form.accountHolderName}
              onChange={(e) => updateField('accountHolderName', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Account Number (masked)"
              value={form.accountNumber}
              onChange={(e) => updateField('accountNumber', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="IFSC Code"
              value={form.ifscCode}
              onChange={(e) => updateField('ifscCode', e.target.value.toUpperCase())}
              disabled={isLoading || isSaving}
            />
            <Input
              label="Bank Name"
              value={form.bankName}
              onChange={(e) => updateField('bankName', e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
        </Card>

        {/* Address */}
        <Card title="Address">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Input
              label="Street Address"
              value={form.streetAddress}
              onChange={(e) => updateField('streetAddress', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="City"
              value={form.city}
              onChange={(e) => updateField('city', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="State"
              value={form.state}
              onChange={(e) => updateField('state', e.target.value)}
              disabled={isLoading || isSaving}
            />
            <Input
              label="PIN Code"
              value={form.pinCode}
              onChange={(e) => updateField('pinCode', e.target.value)}
              disabled={isLoading || isSaving}
            />
          </div>
        </Card>
      </div>

      <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="primary" onClick={handleSaveProfile} disabled={isLoading || isSaving}>
          {isSaving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>
    </PageShell>
  );
}
