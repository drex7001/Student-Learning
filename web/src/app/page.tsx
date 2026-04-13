import Link from "next/link";

const routes = [
  {
    href: "/students",
    kicker: "Teacher Queue",
    title: "See who needs intervention first.",
    body: "Use one concept at a time, rank learners by readiness, and jump into the ones that need support now.",
    tone: "bg-[linear-gradient(135deg,#132034,#203651)] text-white",
  },
  {
    href: "/diagnosis",
    kicker: "Student Diagnosis",
    title: "Focus on one learner and one bottleneck.",
    body: "Use the 3D scene, readiness signal, and targeted explanation without the broader queue noise.",
    tone: "bg-[linear-gradient(135deg,#f6efe3,#ffffff)] text-foreground",
  },
  {
    href: "/concepts",
    kicker: "Concept Explorer",
    title: "Inspect prerequisite routes without student clutter.",
    body: "Trace the concept chain, downstream impact, and graph structure in its own dedicated surface.",
    tone: "bg-[linear-gradient(135deg,#edf6f4,#ffffff)] text-foreground",
  },
];

export default function Home() {
  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <section className="overflow-hidden rounded-[2.6rem] border border-line bg-[radial-gradient(circle_at_top_left,rgba(82,208,197,0.16),transparent_24%),radial-gradient(circle_at_bottom_right,rgba(217,97,61,0.18),transparent_30%),linear-gradient(135deg,#132034,#20324b)] px-6 py-8 text-white shadow-[0_24px_120px_rgba(19,32,52,0.16)] md:px-10 md:py-12">
        <div className="grid gap-10 xl:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-gold">
              UI Direction Reset
            </p>
            <h1 className="mt-5 max-w-5xl text-4xl font-semibold tracking-tight md:text-6xl">
              Stop making one page do every job.
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-8 text-white/76 md:text-lg">
              The product now splits into separate routes for queue, diagnosis, and concept
              exploration. The landing page only introduces those paths and gets the teacher to the
              right workflow quickly.
            </p>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/8 p-6 backdrop-blur">
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-white/60">
              Design intent
            </p>
            <div className="mt-5 grid gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/8 p-4">
                <strong className="block text-lg">One page, one job</strong>
                <p className="mt-2 text-sm leading-7 text-white/72">
                  Home routes you. Diagnosis analyzes one learner. Explorer traces one concept.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/8 p-4">
                <strong className="block text-lg">Less stacked reporting</strong>
                <p className="mt-2 text-sm leading-7 text-white/72">
                  Fewer rails full of cards. More hierarchy, more whitespace, clearer actions.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/8 p-4">
                <strong className="block text-lg">Navigation first</strong>
                <p className="mt-2 text-sm leading-7 text-white/72">
                  The teacher should move between workflows deliberately instead of scanning one giant report.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-5 xl:grid-cols-3">
        {routes.map((route) => (
          <Link
            key={route.href}
            href={route.href}
            className={`group overflow-hidden rounded-[2rem] border border-line p-6 shadow-[0_20px_80px_rgba(19,32,52,0.08)] transition-transform duration-200 hover:-translate-y-1 ${route.tone}`}
          >
            <p className="font-mono text-xs uppercase tracking-[0.24em] opacity-70">{route.kicker}</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight">{route.title}</h2>
            <p className="mt-4 max-w-xl text-sm leading-7 opacity-78">{route.body}</p>
            <span className="mt-8 inline-flex rounded-full border border-current/12 bg-current/8 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.18em]">
              Open route
            </span>
          </Link>
        ))}
      </section>
    </main>
  );
}
