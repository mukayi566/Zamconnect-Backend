-- Create partners table
CREATE TABLE IF NOT EXISTS partners (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organisation_name TEXT NOT NULL,
    organisation_type TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT UNIQUE NOT NULL,
    contact_phone TEXT NOT NULL,
    purpose TEXT NOT NULL,
    website TEXT,
    zicta_license TEXT,
    requested_fields TEXT[] DEFAULT '{}',
    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    sandbox_api_key TEXT UNIQUE NOT NULL,
    production_api_key TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE partners ENABLE ROW LEVEL SECURITY;

-- Create policy for admins (full access)
CREATE POLICY "Admins have full access to partners" 
ON partners FOR ALL 
USING (auth.jwt() ->> 'role' = 'admin');

-- Create policy for public registration (insert only)
CREATE POLICY "Public can apply for partner status" 
ON partners FOR INSERT 
WITH CHECK (true);

-- Create policy for partners to view their own data (using API key or auth)
-- Note: This might need more complex logic if partners authenticate differently
