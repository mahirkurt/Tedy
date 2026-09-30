/**
 * Photo homework contract for a later slice. There is no camera here.
 *
 * The live POST /api/homework/photo still saves on a single upload. This
 * client speaks the two-step shape and does not call it yet:
 *   1. stage=preview  — multipart photo, candidates come back, nothing is saved
 *   2. stage=commit   — the same photo plus the candidates the reader kept
 */

export const PHOTO_HOMEWORK_PATH = '/api/homework/photo';

export type PhotoHomeworkStage = 'preview' | 'commit';
export type PhotoSourceType = 'ted' | 'private';

export interface PhotoFilePart {
  uri: string;
  name: string;
  type: string;
}

/** Fields the vision step is required to return. */
export interface PhotoHomeworkCandidate {
  ders_adi: string;
  odev_basligi: string;
  odev_kaynagi: string;
  son_teslim_tarihi: string;
  odev_durumu: string;
  aciklama: string;
}

interface PhotoHomeworkCommon {
  photo: PhotoFilePart;
  source_type: PhotoSourceType;
  course?: string;
  due_date?: string;
  private_lesson_id?: string;
}

export interface PhotoHomeworkPreviewRequest extends PhotoHomeworkCommon {
  stage: 'preview';
}

export interface PhotoHomeworkCommitRequest extends PhotoHomeworkCommon {
  stage: 'commit';
  selected: PhotoHomeworkCandidate[];
}

export type PhotoHomeworkRequest =
  | PhotoHomeworkPreviewRequest
  | PhotoHomeworkCommitRequest;

/** String fields of the multipart body. The photo part is appended beside them. */
export function photoHomeworkFields(
  request: PhotoHomeworkRequest,
): Record<string, string> {
  const fields: Record<string, string> = {
    stage: request.stage,
    source_type: request.source_type,
  };
  if (request.course) {
    fields.course = request.course;
  }
  if (request.due_date) {
    fields.due_date = request.due_date;
  }
  if (request.private_lesson_id) {
    fields.private_lesson_id = request.private_lesson_id;
  }
  if (request.stage === 'commit') {
    fields.selected = JSON.stringify(request.selected);
  }
  return fields;
}

export function photoHomeworkFormData(request: PhotoHomeworkRequest): FormData {
  const body = new FormData();
  for (const [key, value] of Object.entries(photoHomeworkFields(request))) {
    body.append(key, value);
  }
  body.append('photo', {
    uri: request.photo.uri,
    name: request.photo.name,
    type: request.photo.type,
  } as unknown as Blob);
  return body;
}
