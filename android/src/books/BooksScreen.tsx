import React from 'react';
import {EmptySurface} from '../shell/EmptySurface';

/**
 * Empty shelf. The reader, when it exists, uses theme/books.ts
 * (Literata and Cormorant Garamond), not Carbon Plex.
 */
export function BooksScreen(): React.JSX.Element {
  return (
    <EmptySurface
      title="Tedy Books"
      sentence="Açık bir kitap yok. Raf burada duracak."
    />
  );
}
