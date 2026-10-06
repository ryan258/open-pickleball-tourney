import { encodeBackup, decodeBackup } from './engine.mjs';

export class ConflictError extends Error {}

// The browser lock makes the read/compare/write one operation across open tabs.
// A failed write leaves the previous disk copy intact; the UI retains the new
// tournament in memory and offers a backup without claiming it was saved.
export function createStore(storage, locks, key) {
  let expected = null;
  return {
    read() {
      expected = storage.getItem(key);
      return expected === null ? null : decodeBackup(expected);
    },
    raw() { return expected; },
    changed() {
      try { return storage.getItem(key) !== expected; } catch { return false; }
    },
    async save(tournament) {
      const source = encodeBackup(tournament);
      if (!locks?.request) throw new Error('Automatic saving needs a current browser with secure browser locks. You can still save a backup file.');
      await locks.request(key, () => {
        if (storage.getItem(key) !== expected) throw new ConflictError('Another tab changed this tournament. Load its saved version before making more changes.');
        storage.setItem(key, source);
        expected = source;
      });
    },
    // Deleting is a write: same lock, same stale-tab refusal, so another tab's newer work is never discarded.
    async remove() {
      if (!locks?.request) throw new Error('Automatic saving needs a current browser with secure browser locks, so this saved copy cannot be removed here.');
      await locks.request(key, () => {
        if (storage.getItem(key) !== expected) throw new ConflictError('Another tab changed this tournament. Load its saved version before deleting.');
        storage.removeItem(key);
        expected = null;
      });
    },
  };
}
