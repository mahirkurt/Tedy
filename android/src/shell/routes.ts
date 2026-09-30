export type Role = 'full' | 'reader';

export interface Destination {
  id: string;
  path: string;
  label: string;
  /** Bottom bar. Everything else sits under "Daha fazla". */
  primary: boolean;
  readerAccess: boolean;
}

/**
 * Same map as dashboard/src/routes.ts. Hidden routes (Sınavlar, book
 * chapters, module drafts) stay out of the bar.
 */
export const DESTINATIONS: Destination[] = [
  {id: 'today', path: '/', label: 'Bugün', primary: true, readerAccess: false},
  {
    id: 'work',
    path: '/isler',
    label: 'İşler',
    primary: true,
    readerAccess: false,
  },
  {
    id: 'assistant',
    path: '/asistan',
    label: 'Asistan',
    primary: true,
    readerAccess: false,
  },
  {
    id: 'lessons',
    path: '/dersler',
    label: 'Dersler',
    primary: true,
    readerAccess: false,
  },
  {
    id: 'books',
    path: '/kitaplar',
    label: 'Kitaplar',
    primary: true,
    readerAccess: true,
  },
  {
    id: 'grades',
    path: '/notlar',
    label: 'Notlar',
    primary: false,
    readerAccess: false,
  },
  {
    id: 'calendar',
    path: '/takvim',
    label: 'Takvim',
    primary: false,
    readerAccess: false,
  },
  {
    id: 'teams',
    path: '/takimlar',
    label: 'Takımlar',
    primary: false,
    readerAccess: false,
  },
  {
    id: 'progress',
    path: '/ilerleme',
    label: 'İlerleme',
    primary: false,
    readerAccess: false,
  },
  {
    id: 'announcements',
    path: '/duyurular',
    label: 'Duyurular',
    primary: false,
    readerAccess: false,
  },
  {
    id: 'profile',
    path: '/profil',
    label: 'Profil',
    primary: false,
    readerAccess: false,
  },
  {
    id: 'modules',
    path: '/moduller',
    label: 'Modüller',
    primary: false,
    readerAccess: false,
  },
];

export const MORE_ID = 'more';
export const MORE_LABEL = 'Daha fazla';

export function destinationsFor(role: Role): Destination[] {
  return role === 'full'
    ? DESTINATIONS
    : DESTINATIONS.filter(item => item.readerAccess);
}

export function primaryFor(role: Role): Destination[] {
  return destinationsFor(role).filter(item => item.primary);
}

export function secondaryFor(role: Role): Destination[] {
  return destinationsFor(role).filter(item => !item.primary);
}

/** Full accounts open on Bugün. Readers open on Kitaplar. */
export function homeFor(role: Role): Destination {
  if (role === 'reader') {
    const books = destinationsFor(role).find(item => item.path === '/kitaplar');
    if (books) {
      return books;
    }
  }
  return destinationsFor(role)[0];
}
