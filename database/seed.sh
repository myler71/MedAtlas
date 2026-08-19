#!/bin/bash
set -e
HASH=$(node -e "console.log(require('bcryptjs').hashSync('password123', 12))")
echo "Generated bcrypt hash for password123"
psql -U clinical -d clinical_platform -v ON_ERROR_STOP=1 <<SQL
-- Update users with real bcrypt hash
UPDATE users SET password_hash = '$HASH' WHERE email IN ('dentist@clinic.com', 'ortho@clinic.com');
SELECT email, role FROM users;
SQL
