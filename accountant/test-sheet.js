import { GoogleAuth } from 'google-auth-library';
import fs from 'fs';

const SHEET_ID = '1MzILUGMoncM2D_JZnvYMaJQ5450fT-KlcDvyZDmYEVU';

async function main() {
  try {
    const auth = new GoogleAuth({
      keyFile: './service-account-key.json',
      scopes: ['https://www.googleapis.com/auth/spreadsheets']
    });

    const client = await auth.getClient();
    const token = await client.getAccessToken();
    
    console.log('Access token acquired successfully.');
    
    const res = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}`, {
      headers: {
        Authorization: `Bearer ${token.token}`
      }
    });

    const data = await res.json();
    if (res.ok) {
      console.log('SUCCESS! Spreadsheet Title:', data.properties.title);
      console.log('Tabs:');
      data.sheets.forEach(s => console.log(' -', s.properties.title));
    } else {
      console.log('Google Sheets API response error:', data.error?.message);
      if (data.error?.code === 403 || data.error?.code === 404) {
        const key = JSON.parse(fs.readFileSync('./service-account-key.json', 'utf8'));
        console.log('\nACTION REQUIRED: Please share the sheet with:');
        console.log(key.client_email);
        console.log('Give "Editor" permissions so the app can read/write data.');
      }
    }
  } catch (err) {
    console.error('Error:', err.message);
  }
}

main();
