// Khung tạm cho các trang chưa làm. Khi làm thật thì thay bằng giao diện chính thức.
export default function PagePlaceholder({ code, title, description, todo = [] }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-6">
      {code && (
        <span className="mb-2 inline-block rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
          {code}
        </span>
      )}
      <h1 className="text-2xl font-bold">{title}</h1>
      {description && <p className="mt-2 text-slate-600">{description}</p>}
      {todo.length > 0 && (
        <ul className="mt-4 list-disc space-y-1 pl-6 text-sm text-slate-600">
          {todo.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
