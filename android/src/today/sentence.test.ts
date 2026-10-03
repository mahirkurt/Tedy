import {parseHealth, todaySentence} from './sentence';

test('turns health and the signed-in name into a sentence', () => {
  const health = parseHealth({
    success: true,
    timestamp: '2026-09-30T15:00:00.000Z',
    scrape_errors: [],
    staleness: {last_successful_full_scrape: '2026-09-30T15:00:00.000Z'},
    error: 'Unauthorized',
  });
  const sentence = todaySentence({
    name: 'Işık',
    health,
    problem: 'none',
  });
  expect(sentence.startsWith('Işık, okul verisi')).toBe(true);
  expect(sentence.endsWith('.')).toBe(true);
  expect(sentence).not.toMatch(/unauthorized|forbidden|\{|\}/i);
});

test('a failed call stays a sentence and drops raw error tokens', () => {
  const sentence = todaySentence({
    name: '',
    health: null,
    problem: 'unreachable',
  });
  expect(sentence).toBe('Panele şu an ulaşılamıyor. Biraz sonra yeniden dene.');
  expect(parseHealth({error: 'Not authenticated'})).toBeNull();
});
