export type HealthProblem = 'none' | 'unreachable' | 'session';

export interface HealthSnapshot {
  success: boolean;
  timestamp: string;
  lastSuccessful: string;
  errorCount: number;
}

export function parseHealth(data: unknown): HealthSnapshot | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }
  const row = data as Record<string, unknown>;
  if (typeof row.error === 'string' && typeof row.success !== 'boolean') {
    return null;
  }
  const staleness =
    row.staleness && typeof row.staleness === 'object'
      ? (row.staleness as Record<string, unknown>)
      : {};
  return {
    success: row.success === true,
    timestamp: typeof row.timestamp === 'string' ? row.timestamp : '',
    lastSuccessful:
      typeof staleness.last_successful_full_scrape === 'string'
        ? staleness.last_successful_full_scrape
        : '',
    errorCount: Array.isArray(row.scrape_errors) ? row.scrape_errors.length : 0,
  };
}

/** Empty string when the value is not a real timestamp. Never echo the raw input. */
export function formatTurkishTimestamp(value: string): string {
  if (!value.trim()) {
    return '';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '';
  }
  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(parsed);
}

export function todaySentence(input: {
  name: string;
  health: HealthSnapshot | null;
  problem: HealthProblem;
}): string {
  if (input.problem === 'session') {
    return 'Oturumun kapandı. Yeniden giriş yap.';
  }
  if (input.problem === 'unreachable' || !input.health) {
    return 'Panele şu an ulaşılamıyor. Biraz sonra yeniden dene.';
  }
  const name = input.name.trim();
  const when = formatTurkishTimestamp(
    input.health.lastSuccessful || input.health.timestamp,
  );
  if (!input.health.success || input.health.errorCount > 0) {
    const lead = name
      ? `${name}, son tarama eksik kaldı.`
      : 'Son tarama eksik kaldı.';
    return when ? `${lead} Elimizdeki son kayıt ${when}.` : lead;
  }
  if (when) {
    return name
      ? `${name}, okul verisi ${when} itibarıyla güncel.`
      : `Okul verisi ${when} itibarıyla güncel.`;
  }
  return name
    ? `${name}, bugün için kayıtlı bir tarama zamanı yok.`
    : 'Bugün için kayıtlı bir tarama zamanı yok.';
}
