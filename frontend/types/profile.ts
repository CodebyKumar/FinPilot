export interface Address {
  line1: string;
  line2?: string;
  city: string;
  district: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface BankDetails {
  account_holder_name: string;
  bank_name: string;
  account_number: string;
  ifsc: string;
  branch: string;
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
}

export interface TaxPreferences {
  subscribe_newsletter: boolean;
  marketing_consent: boolean;
  terms_accepted: boolean;
}

export interface Profile {
  id?: string;
  full_name: string;
  first_name: string;
  middle_name?: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  marital_status: string;
  nationality: string;
  phone: string;
  alternate_phone?: string;
  email: string;
  father_name?: string;
  mother_name?: string;
  occupation: string;
  employer?: string;
  designation?: string;
  annual_income?: string;
  pan?: string;
  aadhaar?: string;
  passport_number?: string;
  voter_id?: string;
  address: Address;
  permanent_address?: Address;
  bank_details?: BankDetails;
  emergency_contact?: EmergencyContact;
  preferences?: TaxPreferences;
  created_at?: string;
  updated_at?: string;
}
