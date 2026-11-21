'use client';

import { useEffect, useState, type ChangeEvent } from 'react';
import { CardHeader } from '@/components/ui/card-header';
import { Icon } from '@/components/ui/icon';
import { inspectPanelPhotoAction, type PhotoVerdict } from '../actions';

/** 1x1 transparent GIF shown until a photo is chosen. */
const BLANK_IMAGE = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';
/** The inspection API accepts about 8 MB of image. */
const MAX_PHOTO_BYTES = 8 * 1024 * 1024;

const CONDITION_LABELS: Record<string, string> = {
  clean: 'Clean',
  dusty: 'Dusty',
  bird_drop: 'Bird droppings',
  electrical_damage: 'Electrical damage',
  physical_damage: 'Physical damage',
};

/** idle → checking → a verdict, the demo result (no model in the mock demo), or an error message. */
type Check =
  | { state: 'idle' }
  | { state: 'checking' }
  | { state: 'verdict'; verdict: PhotoVerdict }
  | { state: 'demo' }
  | { state: 'error'; message: string };

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error('Could not read the photo'));
    reader.readAsDataURL(file);
  });
}

/**
 * Photo upload checked by the backend's panel-inspection model (POST /api/vision/inspect). The mock demo
 * has no model, so it shows a fixed result labelled as a demo. The output-loss figures are the
 * per-class derates in the backend's src/vision/cctv_panel_monitor.py.
 */
export function PhotoCheck() {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [check, setCheck] = useState<Check>({ state: 'idle' });

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const onChoose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setPreviewUrl(URL.createObjectURL(file));
    if (file.size > MAX_PHOTO_BYTES) {
      setCheck({
        state: 'error',
        message: 'That photo is larger than 8 MB. Choose a smaller one.',
      });
      return;
    }
    setCheck({ state: 'checking' });
    try {
      const result = await inspectPanelPhotoAction(await readAsDataUrl(file));
      if (!result.ok) setCheck({ state: 'error', message: result.error });
      else setCheck(result.data ? { state: 'verdict', verdict: result.data } : { state: 'demo' });
    } catch {
      setCheck({ state: 'error', message: 'Your photo could not be read. Try another one.' });
    }
  };

  const reset = () => {
    setPreviewUrl(null);
    setCheck({ state: 'idle' });
  };

  return (
    <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
      <CardHeader title="Check a panel photo" subtitle="Detects dust, droppings and damage" />
      <div className="drop" id="drop">
        <div id="drop-empty" hidden={previewUrl !== null}>
          <Icon name="camera" size="lg" style={{ color: 'var(--primary)' }} />
          <p style={{ margin: '8px 0 12px' }}>JPG or PNG · max 8 MB · daylight, front-on</p>
          <label className="btn btn-primary" htmlFor="photo">
            <Icon name="upload" />
            Choose photo
          </label>
          <input
            type="file"
            id="photo"
            accept="image/png,image/jpeg"
            className="sr-only"
            onChange={(event) => void onChoose(event)}
          />
        </div>
        <div id="drop-res" hidden={previewUrl === null} aria-live="polite">
          {/* A blob: URL from the user's own file; next/image cannot optimise it. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img id="photo-prev" alt="Your uploaded panel photo" src={previewUrl ?? BLANK_IMAGE} />
          <PhotoResult check={check} />
          <button
            className="btn btn-secondary btn-sm"
            type="button"
            id="photo-reset"
            style={{ marginTop: 12 }}
            onClick={reset}
          >
            Try another photo
          </button>
        </div>
      </div>
    </div>
  );
}

function PhotoResult({ check }: { check: Check }) {
  if (check.state === 'checking') return <p className="small muted">Checking your photo…</p>;
  if (check.state === 'error') {
    return (
      <p className="small" role="alert">
        {check.message}
      </p>
    );
  }
  if (check.state === 'verdict') {
    const { verdict } = check;
    return (
      <>
        <div className="row" style={{ justifyContent: 'center' }}>
          <span className={`badge ${verdict.requiresCleaning ? 'b-warn' : 'b-ok'}`}>
            {`${CONDITION_LABELS[verdict.condition] ?? verdict.condition} · ${verdict.severity.toLowerCase()} severity`}
          </span>
          <span className="badge b-neutral">{`${Math.round(verdict.confidence * 100)}% sure`}</span>
        </div>
        <p className="small muted" style={{ marginTop: 8 }}>
          {verdict.recommendedAction}
        </p>
      </>
    );
  }
  if (check.state === 'demo') {
    return (
      <>
        <div className="row" style={{ justifyContent: 'center' }}>
          <span className="badge b-warn">Dusty · medium severity</span>
          <span className="badge b-neutral">Demo result</span>
        </div>
        <p className="small muted" style={{ marginTop: 8 }}>
          Your photo is not analysed yet. When the panel-inspection model finds dust it assumes
          about 5% output loss (bird droppings 12%, electrical damage 25%, physical damage 35%).
        </p>
      </>
    );
  }
  return null;
}
