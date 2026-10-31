export default function SectionCard({ title, children }) {
  return (
    <article className="card animate-fadeUp p-5 sm:p-6">
      <h3 className="mb-3 text-base font-semibold text-white">{title}</h3>
      {children}
    </article>
  );
}
