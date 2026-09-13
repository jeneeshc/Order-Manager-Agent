import { GoogleAuth } from 'google-auth-library';
import fs from 'fs';

const SHEET_ID = '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA';

async function main() {
  try {
    const auth = new GoogleAuth({
      keyFile: './service-account-key.json',
      scopes: ['https://www.googleapis.com/auth/spreadsheets']
    });

    const client = await auth.getClient();
    const token = await client.getAccessToken();

    const res = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}`, {
      headers: { Authorization: `Bearer ${token.token}` }
    });

    const data = await res.json();
    if (!res.ok) {
      console.log('SHEET_ACCESS_ERROR:', data.error?.code, data.error?.message);
      const key = JSON.parse(fs.readFileSync('./service-account-key.json', 'utf8'));
      console.log('SERVICE_ACCOUNT_EMAIL:', key.client_email);
      return;
    }

    console.log('SPREADSHEET_TITLE:', data.properties.title);
    console.log('EXISTING_TABS:');
    for (const s of data.sheets) {
      const title = s.properties.title;
      console.log(`\n--- TAB: "${title}" ---`);
      // Fetch headers (row 1 & row 2)
      const rangeRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(title)}!A1:Z5`, {
        headers: { Authorization: `Bearer ${token.token}` }
      });
      const rangeData = await rangeRes.json();
      if (rangeData.values && rangeData.values.length > 0) {
        console.log('Headers (Row 1):', JSON.stringify(rangeData.values[0]));
        if (rangeData.values.length > 1) {
          console.log('Sample Row 2:', JSON.stringify(rangeData.values[1]));
        }
      } else {
        console.log('(Tab is empty)');
      }
    }
  } catch (err) {
    console.error('Error:', err.message);
  }
}

main();
