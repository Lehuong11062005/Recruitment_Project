import Icon from './Icon';
import { PIPELINE_STATUS } from '../constants/status';

const BASE_STEPS = [
  { key: PIPELINE_STATUS.APPLIED, label: 'Đã nộp' },
  { key: PIPELINE_STATUS.SCREENING, label: 'Đang sơ loại' },
  { key: PIPELINE_STATUS.INTERVIEW, label: 'Hẹn phỏng vấn' },
  { key: 'RESULT', label: 'Kết quả' },
];

function resolveStepStates(status) {
  if (status === PIPELINE_STATUS.HIRED) {
    return [
      { ...BASE_STEPS[0], state: 'done' },
      { ...BASE_STEPS[1], state: 'done' },
      { ...BASE_STEPS[2], state: 'done' },
      { key: 'RESULT', label: 'Kết quả: Trúng tuyển', state: 'hired' },
    ];
  }

  if (status === PIPELINE_STATUS.REJECTED) {
    return [
      { ...BASE_STEPS[0], state: 'done' },
      { ...BASE_STEPS[1], state: 'muted' },
      { ...BASE_STEPS[2], state: 'muted' },
      { key: 'RESULT', label: 'Kết quả: Từ chối', state: 'rejected' },
    ];
  }

  const activeIndex =
    status === PIPELINE_STATUS.INTERVIEW
      ? 2
      : status === PIPELINE_STATUS.SCREENING
        ? 1
        : 0;

  return BASE_STEPS.map((step, index) => ({
    ...step,
    state: index < activeIndex ? 'done' : index === activeIndex ? 'active' : 'pending',
  }));
}

export default function PipelineProgress({ status, compact = false }) {
  const steps = resolveStepStates(status);

  return (
    <ol
      className={`pipeline-stepper ${compact ? 'compact' : ''}`}
      aria-label="Tiến trình xử lý hồ sơ"
    >
      {steps.map((step, index) => (
        <li key={step.key} className={`pipeline-step is-${step.state}`}>
          <span className="pipeline-step-dot" aria-hidden="true">
            {step.state === 'done' || step.state === 'hired' ? (
              <Icon name="check" size={compact ? 11 : 13} />
            ) : step.state === 'rejected' ? (
              '×'
            ) : (
              index + 1
            )}
          </span>
          <span className="pipeline-step-label">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}
