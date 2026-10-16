import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <div className="py-24">
      <h1 className="text-[28px] font-semibold tracking-tight">Not found</h1>
      <Link to="/" className="mt-4 inline-block text-accent">
        Go to People
      </Link>
    </div>
  )
}
