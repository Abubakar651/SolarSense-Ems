'use client';

import { useEffect, useState, type ChangeEvent } from 'react';
import { CardHeader } from '@/components/ui/card-header';
import { Icon } from '@/components/ui/icon';

/** 1x1 transparent GIF shown until a photo is chosen. */
const BLANK_IMAGE = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';

/**
 * Photo upload with a sample result. The classifier is not wired up yet, so the verdict is a
 * fixed demo and is labelled as one. The output-loss figures are the per-class derates in the
 * backend's src/vision/cctv_panel_monitor.py.
 */
export function PhotoCheck() {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const onChoose = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) setPreviewUrl(URL.createObjectURL(file));
  };

  return (
    <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
      <CardHeader
        title="Check a panel photo"
        subtitle="Upload a picture of your array. The inspection model classifies it as clean, dusty, bird droppings, electrical damage or physical damage."
      />
      <div className="drop" id="drop">
        <div id="drop-empty" hidden={previewUrl !== null}>
          <Icon name="camera" size="lg" style={{ color: 'var(--primary)' }} />
          <p style={{ margin: '8px 0 12px' }}>
            JPG or PNG, up to 10 MB. Take the photo from the front, in daylight.
          </p>
          <label className="btn btn-primary" htmlFor="photo">
            <Icon name="upload" />
            Choose photo
          </label>
          <input
            type="file"
            id="photo"
            accept="image/png,image/jpeg"
            className="sr-only"
            onChange={onChoose}
          />
        </div>
        <div id="drop-res" hidden={previewUrl === null} aria-live="polite">
          {/* A blob: URL from the user's own file; next/image cannot optimise it. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img id="photo-prev" alt="Your uploaded panel photo" src={previewUrl ?? BLANK_IMAGE} />
          <div className="row" style={{ justifyContent: 'center' }}>
            <span className="badge b-warn">Dusty · medium severity</span>
            <span className="badge b-neutral">Demo result</span>
          </div>
          <p className="small muted" style={{ marginTop: 8 }}>
            Your photo is not analysed yet. When the panel-inspection model finds dust it assumes
            about 5% output loss (bird droppings 12%, electrical damage 25%, physical damage 35%).
          </p>
          <button
            className="btn btn-secondary btn-sm"
            type="button"
            id="photo-reset"
            style={{ marginTop: 12 }}
            onClick={() => setPreviewUrl(null)}
          >
            Try another photo
          </button>
        </div>
      </div>
    </div>
  );
}
