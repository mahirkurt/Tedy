import {photoHomeworkFields, photoHomeworkFormData} from './photoHomework';

const photo = {
  uri: 'file:///tmp/odev.jpg',
  name: 'odev.jpg',
  type: 'image/jpeg',
};

const candidate = {
  ders_adi: 'Matematik',
  odev_basligi: 'Sayfa 12',
  odev_kaynagi: '',
  son_teslim_tarihi: '',
  odev_durumu: '',
  aciklama: '',
};

test('preview then commit are different multipart stages', () => {
  const preview = photoHomeworkFields({
    stage: 'preview',
    photo,
    source_type: 'ted',
    course: 'Matematik',
  });
  const commit = photoHomeworkFields({
    stage: 'commit',
    photo,
    source_type: 'private',
    private_lesson_id: 'lesson-1',
    selected: [candidate],
  });

  expect(preview.stage).toBe('preview');
  expect(preview).not.toHaveProperty('selected');
  expect(commit.stage).toBe('commit');
  expect(commit.selected).toContain('Sayfa 12');
  expect(commit.private_lesson_id).toBe('lesson-1');

  expect(
    photoHomeworkFormData({stage: 'preview', photo, source_type: 'ted'}),
  ).toBeInstanceOf(FormData);
  expect(
    photoHomeworkFormData({
      stage: 'commit',
      photo,
      source_type: 'private',
      selected: [candidate],
    }),
  ).toBeInstanceOf(FormData);
});
