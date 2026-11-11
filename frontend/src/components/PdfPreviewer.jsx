import { useEffect, useState } from 'react';
import Icon from './Icon';
import { applicationService } from '../services/applicationService';

function messageFor(error) {
  if (error?.status === 404) return 'Không tìm thấy file PDF CV của hồ sơ này.';
  if (error?.status === 403) return 'Bạn không có quyền xem CV của hồ sơ này.';
  if (error?.code === 'NOT_PDF') return 'File CV trả về không phải PDF hợp lệ.';
  return error?.message || 'Không thể tải file PDF CV.';
}

function Skeleton({ height }) {
  return (
    <div aria-busy="true" role="status" aria-label="Đang tải file PDF CV" className="animate-pulse space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-5" style={{ height }}>
      <div className="h-5 w-1/3 rounded bg-slate-200" />
      <div className="h-3 w-full rounded bg-slate-200" />
      <div className="h-3 w-11/12 rounded bg-slate-200" />
      <div className="h-3 w-4/5 rounded bg-slate-200" />
      <div className="h-3/5 w-full rounded bg-slate-200" />
    </div>
  );
}

function PdfPreviewerInner({ applicationId, fileName, height, onReload }) {
  const [state, setState] = useState({ phase: 'loading', url: '', message: '' });

  useEffect(() => {
    let active = true;
    let objectUrl = '';
    const controller = new AbortController();

    // iframe không gửi được header Authorization -> tải PDF bằng axios (có JWT) rồi tạo blob URL.
    applicationService.getCvBlob(applicationId, { signal: controller.signal })
      .then((blob) => {
        if (!active) return;
        if (!(blob instanceof Blob) || blob.size === 0) {
          throw Object.assign(new Error('empty'), { code: 'NOT_PDF' });
        }
        if (blob.type && !blob.type.includes('pdf')) {
          throw Object.assign(new Error('not pdf'), { code: 'NOT_PDF' });
        }
        objectUrl = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
        setState({ phase: 'ready', url: objectUrl, message: '' });
      })
      .catch((error) => {
        if (active) setState({ phase: 'error', url: '', message: messageFor(error) });
      });

    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [applicationId]);

  const ready = state.phase === 'ready';
  const downloadName = fileName || `cv_${applicationId}.pdf`;

  return (
    <section className="card" aria-label="Xem trước CV">
      <div className="card-header">
        <div>
          <h3 className="section-title">CV gốc của ứng viên</h3>
          <p className="muted small">Xem trực tiếp file PDF đã nộp.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {ready ? (
            <>
              <a className="btn btn-secondary" href={state.url} target="_blank" rel="noreferrer">Mở tab mới</a>
              <a className="btn btn-primary" href={state.url} download={downloadName}><Icon name="download" size={15} />Tải xuống CV</a>
            </>
          ) : (
            <button type="button" className="btn btn-primary disabled:opacity-50" disabled><Icon name="download" size={15} />Tải xuống CV</button>
          )}
        </div>
      </div>

      {state.phase === 'loading' && <Skeleton height={height} />}

      {state.phase === 'error' && (
        <div className="alert-box alert-error flex flex-wrap items-center justify-between gap-3" role="alert">
          <span className="flex items-center gap-2"><Icon name="warning" size={18} />{state.message}</span>
          <button type="button" className="btn btn-secondary" onClick={onReload}>Thử lại</button>
        </div>
      )}

      {ready && (
        <iframe
          title="Xem trước CV PDF"
          src={`${state.url}#view=FitH`}
          className="w-full rounded-lg border border-slate-200"
          style={{ height }}
        />
      )}
    </section>
  );
}

/**
 * Trình xem trước PDF CV (Task 8.3).
 * Dùng: <PdfPreviewer applicationId={id} fileName="CV-NguyenVanA.pdf" />
 * Đổi applicationId hoặc bấm "Thử lại" sẽ remount (key) nên state luôn quay về loading.
 */
export default function PdfPreviewer({ applicationId, fileName = '', height = 720 }) {
  const [reloadKey, setReloadKey] = useState(0);
  if (!applicationId) {
    return <section className="card empty-state"><strong>Chưa chọn hồ sơ</strong><p>Chọn một hồ sơ để xem CV.</p></section>;
  }
  return (
    <PdfPreviewerInner
      key={`${applicationId}:${reloadKey}`}
      applicationId={applicationId}
      fileName={fileName}
      height={height}
      onReload={() => setReloadKey((k) => k + 1)}
    />
  );
}
