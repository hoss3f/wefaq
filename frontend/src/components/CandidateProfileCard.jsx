function InfoRows({ items }) {
  const visible = items.filter(([, value]) => value !== null && value !== undefined && value !== '')
  if (!visible.length) return null
  return <dl className="divide-y divide-teal-50">{visible.map(([label, value]) => <div key={label} className="flex items-start justify-between gap-5 py-2.5 text-sm"><dt className="text-muted">{label}</dt><dd className="text-left font-medium text-ink">{value}</dd></div>)}</dl>
}

function ProfileSection({ title, children }) {
  if (!children) return null
  return <section className="border-t border-teal-100 pt-5"><h3 className="mb-2 font-display text-xl text-teal-700">{title}</h3>{children}</section>
}

function TextSection({ title, value }) {
  if (!value) return null
  return <ProfileSection title={title}><p className="whitespace-pre-wrap text-sm leading-7 text-ink">{value}</p></ProfileSection>
}

export default function CandidateProfileCard({ candidate, compatibility, position, children }) {
  const preferredNationalities = Array.isArray(candidate?.preferred_nationalities)
    ? candidate.preferred_nationalities
    : candidate?.preferred_nationalities ? [candidate.preferred_nationalities] : []
  const preferredAge = candidate?.preferred_age_min != null && candidate?.preferred_age_max != null
    ? `${candidate.preferred_age_min}–${candidate.preferred_age_max} سنة`
    : null

  return (
    <article className="overflow-hidden rounded-3xl border border-teal-100 bg-white shadow-sm">
      <div className="relative bg-teal-700 px-5 py-5 text-linen sm:px-6">
        <div className="absolute inset-0 opacity-10 mashrabiya-bg" />
        <div className="relative flex items-center gap-4">
          <div aria-label="صورة المرشح مخفية" className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full border border-linen/40 bg-linen/10 text-center text-xs leading-tight">الصورة<br />مخفية</div>
          <div className="min-w-0 flex-1"><p className="text-sm text-linen/75">ملف مرشح مناسب</p><div className="mt-1 flex items-end gap-2"><strong className="font-display text-4xl leading-none">{compatibility == null ? '—' : `${compatibility}%`}</strong><span className="pb-1 text-xs text-linen/75">توافق إرشادي</span></div></div>
          {position && <span className="shrink-0 rounded-full bg-linen/10 px-3 py-1 text-xs">{position}</span>}
        </div>
      </div>

      <div className="space-y-5 p-5 sm:p-6">
        <ProfileSection title="المعلومات الأساسية"><InfoRows items={[
          ['العمر', candidate?.age != null ? `${candidate.age} سنة` : null],
          ['الجنسية', candidate?.nationality], ['بلد الإقامة', candidate?.country],
          ['الحالة الاجتماعية', candidate?.marital_status],
        ]} /></ProfileSection>

        <ProfileSection title="الدراسة والعمل"><InfoRows items={[
          ['المؤهل الدراسي', candidate?.education], ['المهنة', candidate?.profession],
        ]} /></ProfileSection>

        <ProfileSection title="المعلومات الشخصية"><InfoRows items={[
          ['الطول', candidate?.height != null ? `${candidate.height} سم` : null],
          ['القوام', candidate?.body_type], ['لون البشرة', candidate?.skin_tone],
        ]} /></ProfileSection>

        <TextSection title="عن المرشح" value={candidate?.profile_description} />

        <ProfileSection title="عن الزواج"><InfoRows items={[
          ['موعد الزواج المفضل', candidate?.marriage_timeline],
          ['لديه أطفال', candidate?.has_children],
          ['عدد الأطفال', candidate?.has_children === 'نعم' ? candidate?.kids_count : null],
          ['قبول التعدد', candidate?.polygyny_acceptance],
        ]} />{candidate?.marriage_expectations && <p className="mt-3 text-sm leading-7 text-ink">{candidate.marriage_expectations}</p>}</ProfileSection>

        {(preferredAge || preferredNationalities.length || candidate?.preferred_marital_status) && <ProfileSection title="التفضيلات"><InfoRows items={[
          ['العمر المناسب للشريك', preferredAge], ['الحالة الاجتماعية المفضلة', candidate?.preferred_marital_status],
          ['الزواج من خارج البلد', candidate?.marriage_country_preference], ['أهم صفة في شريك الحياة', candidate?.partner_priority],
        ]} />{preferredNationalities.length > 0 && <div className="pt-3"><p className="mb-2 text-xs text-muted">الجنسيات المفضلة للشريك</p><div className="flex flex-wrap gap-2">{preferredNationalities.map((item) => <span key={item} className="rounded-full bg-teal-50 px-3 py-1.5 text-xs text-teal-700">{item}</span>)}</div></div>}</ProfileSection>}

        <TextSection title="عن شريك الحياة" value={candidate?.partner_description} />
        {children}
      </div>
    </article>
  )
}
