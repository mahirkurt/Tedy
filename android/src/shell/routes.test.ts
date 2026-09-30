import {homeFor, primaryFor, secondaryFor, destinationsFor} from './routes';

test('full role home is Bugün', () => {
  expect(homeFor('full').label).toBe('Bugün');
  expect(homeFor('full').path).toBe('/');
  expect(primaryFor('full').map(item => item.label)).toEqual([
    'Bugün',
    'İşler',
    'Asistan',
    'Dersler',
    'Kitaplar',
  ]);
  expect(secondaryFor('full').map(item => item.label)).toEqual([
    'Notlar',
    'Takvim',
    'Takımlar',
    'İlerleme',
    'Duyurular',
    'Profil',
    'Modüller',
  ]);
});

test('reader role home is Kitaplar', () => {
  expect(homeFor('reader').label).toBe('Kitaplar');
  expect(homeFor('reader').path).toBe('/kitaplar');
  expect(destinationsFor('reader').map(item => item.label)).toEqual([
    'Kitaplar',
  ]);
  expect(secondaryFor('reader')).toEqual([]);
});
