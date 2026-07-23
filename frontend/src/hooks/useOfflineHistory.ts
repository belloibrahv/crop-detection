/**
 * Offline diagnosis history cache backed by IndexedDB (via the `idb` library).
 *
 * - Writes every successful diagnosis to IDB.
 * - Exposes cached records so History can show them even without a network.
 * - Keeps at most MAX_RECORDS entries (oldest pruned first).
 */
import { openDB, type IDBPDatabase } from 'idb'
import { useEffect, useState, useCallback } from 'react'

const DB_NAME = 'agroscan'
const STORE = 'diagnosis_history'
const MAX_RECORDS = 20

export interface CachedDiagnosis {
  diagnosis_id: string
  predicted_class_id: number | null
  confidence_score: number | null
  top3_predictions: Array<{
    class_id: number
    crop: string
    disease: string
    is_healthy: boolean
    confidence: number
  }>
  created_at: string
}

async function getDB(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'diagnosis_id' })
        store.createIndex('created_at', 'created_at')
      }
    },
  })
}

/** Persist a diagnosis record to IDB, pruning oldest if over MAX_RECORDS. */
export async function cacheDiagnosis(record: CachedDiagnosis): Promise<void> {
  const db = await getDB()
  const tx = db.transaction(STORE, 'readwrite')
  await tx.store.put(record)

  // Prune oldest entries beyond the limit
  const all = await tx.store.index('created_at').getAllKeys()
  if (all.length > MAX_RECORDS) {
    const toDelete = all.slice(0, all.length - MAX_RECORDS)
    for (const key of toDelete) {
      await tx.store.delete(key)
    }
  }
  await tx.done
}

/** Load all cached diagnoses, most-recent first. */
export async function loadCachedHistory(): Promise<CachedDiagnosis[]> {
  const db = await getDB()
  const all = await db.getAllFromIndex(STORE, 'created_at')
  return all.reverse()
}

/** Delete a single entry from IDB. */
export async function deleteCachedDiagnosis(id: string): Promise<void> {
  const db = await getDB()
  await db.delete(STORE, id)
}

// ─── React hook ───────────────────────────────────────────────────────────────

export function useOfflineHistory() {
  const [cachedRecords, setCachedRecords] = useState<CachedDiagnosis[]>([])
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    loadCachedHistory().then(setCachedRecords).catch(() => {})
  }, [])

  useEffect(() => {
    const on = () => setIsOnline(true)
    const off = () => setIsOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])

  const refresh = useCallback(async () => {
    const records = await loadCachedHistory()
    setCachedRecords(records)
  }, [])

  return { cachedRecords, isOnline, refresh }
}
