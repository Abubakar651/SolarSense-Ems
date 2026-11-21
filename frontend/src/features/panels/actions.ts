'use server';

import { revalidatePath } from 'next/cache';
import { attempt, fail, ok, text, type ActionResult } from '@/services/http/action-result';
import { apiFetch } from '@/services/http/client';
import { usingMocks } from '@/services/mode';

/** What the panel-inspection model says about one photo (from POST /api/vision/inspect). */
export interface PhotoVerdict {
  condition: string;
  confidence: number;
  severity: string;
  requiresCleaning: boolean;
  recommendedAction: string;
}

interface InspectDto {
  condition: string;
  confidence: number;
  severity: string;
  requires_cleaning: boolean;
  recommended_action: string;
}

/** About 8 MB of image once base64-encoded; the API refuses anything larger. */
const MAX_DATA_URL_CHARS = 11_000_000;

/** Sends a photo (as a data: URL) to the inspection model. Null in the mock demo, which has no model. */
export async function inspectPanelPhotoAction(
  dataUrl: unknown,
): Promise<ActionResult<PhotoVerdict | null>> {
  if (usingMocks()) return ok(null);
  const image = text(dataUrl, MAX_DATA_URL_CHARS);
  if (!image || !image.startsWith('data:image/')) return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<InspectDto>('/api/vision/inspect', {
      method: 'POST',
      body: { base64_image: image, use_tta: true },
    }),
  );
  if (!result.ok) {
    // The model weights are not on every server; any server-side failure means "not available".
    return result.code === 'validation_error' ? result : fail('vision_unavailable');
  }
  const dto = result.data;
  return ok({
    condition: dto.condition,
    confidence: dto.confidence,
    severity: dto.severity,
    requiresCleaning: dto.requires_cleaning,
    recommendedAction: dto.recommended_action,
  });
}

/**
 * Records that the panels were washed today (POST /api/panels/washes): the dust model restarts from
 * today. A no-op in the mock demo, whose dust figures are sample data.
 */
export async function recordPanelWashAction(): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const result = await attempt(() => apiFetch<unknown>('/api/panels/washes', { method: 'POST' }));
  if (!result.ok) return result;
  // The Panels screen, the dashboard's dust card and the alerts all read the dust model.
  revalidatePath('/', 'layout');
  return ok();
}
