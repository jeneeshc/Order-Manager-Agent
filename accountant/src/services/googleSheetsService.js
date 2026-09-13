// Backward-compatible re-export: GoogleSheetsService -> DatabaseService (Native Cloud Firestore)
export * from './databaseService';
export { databaseService as googleSheetsService, databaseService as default } from './databaseService';
