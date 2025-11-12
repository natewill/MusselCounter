/**
 * Storage utilities using localforage for robust localStorage with fallbacks
 */
import localforage from 'localforage';

// Configure localforage
localforage.config({
  name: 'MusselCounter',
  storeName: 'musselCounterStorage',
  description: 'MusselCounter application storage',
  driver: [localforage.INDEXEDDB, localforage.WEBSQL, localforage.LOCALSTORAGE],
  size: 4980736, // ~5MB
  version: 1.0,
});

/**
 * Safely get an item from storage
 */
export async function safeGetItem(key) {
  try {
    return await localforage.getItem(key);
  } catch (error) {
    console.warn(`Failed to get storage item "${key}":`, error);
    return null;
  }
}

/**
 * Safely set an item in storage
 */
export async function safeSetItem(key, value) {
  try {
    await localforage.setItem(key, value);
    return true;
  } catch (error) {
    console.warn(`Failed to set storage item "${key}":`, error);
    return false;
  }
}

/**
 * Safely remove an item from storage
 */
export async function safeRemoveItem(key) {
  try {
    await localforage.removeItem(key);
    return true;
  } catch (error) {
    console.warn(`Failed to remove storage item "${key}":`, error);
    return true; // Still return true as item may not exist
  }
}

/**
 * Safely get and parse JSON from storage
 */
export async function safeGetJSON(key) {
  try {
    const value = await localforage.getItem(key);
    if (value === null) {
      return null;
    }
    // localforage already handles JSON, but we'll parse if it's a string
    if (typeof value === 'string') {
      return JSON.parse(value);
    }
    return value;
  } catch (error) {
    console.warn(`Failed to parse JSON from storage item "${key}":`, error);
    return null;
  }
}

/**
 * Safely set JSON in storage
 */
export async function safeSetJSON(key, value) {
  try {
    await localforage.setItem(key, value);
    return true;
  } catch (error) {
    console.warn(`Failed to stringify JSON for storage item "${key}":`, error);
    return false;
  }
}

/**
 * Safely get a number from storage
 */
export async function safeGetNumber(key) {
  try {
    const value = await localforage.getItem(key);
    if (value === null || value === undefined) {
      return null;
    }
    
    const num = Number(value);
    if (isNaN(num)) {
      console.warn(`Invalid number in storage item "${key}":`, value);
      return null;
    }
    
    return num;
  } catch (error) {
    console.warn(`Failed to get number from storage item "${key}":`, error);
    return null;
  }
}
