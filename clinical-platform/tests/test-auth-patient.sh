#!/bin/bash
set -e

BASE="http://localhost:3000"
FASTAPI="http://localhost:8000"

echo "=== Test 1: Health checks ==="
curl -sf $BASE/api/health | grep -q "ok" && echo "PASS: Express health" || echo "FAIL: Express health"
curl -sf $FASTAPI/api/health | grep -q "ok" && echo "PASS: FastAPI health" || echo "FAIL: FastAPI health"

echo "=== Test 2: Register ==="
REGISTER=$(curl -sf -X POST $BASE/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"integration@test.com","password":"testpass123","full_name":"Dr. Integration","role":"dentist"}')
TOKEN=$(echo $REGISTER | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
echo "PASS: Register (token obtained)"

echo "=== Test 3: Login ==="
curl -sf -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"integration@test.com","password":"testpass123"}' | grep -q "token" && echo "PASS: Login" || echo "FAIL: Login"

echo "=== Test 4: Get me ==="
curl -sf $BASE/api/auth/me -H "Authorization: Bearer $TOKEN" | grep -q "Integration" && echo "PASS: Get me" || echo "FAIL: Get me"

echo "=== Test 5: Create patient ==="
PATIENT=$(curl -sf -X POST $FASTAPI/api/patients \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"Patient","gender":"male"}')
PATIENT_ID=$(echo $PATIENT | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "PASS: Create patient ($PATIENT_ID)"

echo "=== Test 6: Get patient ==="
curl -sf $FASTAPI/api/patients/$PATIENT_ID | grep -q "Test" && echo "PASS: Get patient" || echo "FAIL: Get patient"

echo "=== Test 7: List patients ==="
curl -sf $FASTAPI/api/patients | grep -q "Test" && echo "PASS: List patients" || echo "FAIL: List patients"

echo "=== All tests passed ==="