import { redirect } from 'next/navigation'

interface RootPageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

export default async function RootPage({ searchParams }: RootPageProps) {
  const params = await searchParams
  const cat = typeof params.cat === 'string' ? params.cat : undefined
  const target = cat === 'games' ? '/games' : cat === 'music' ? '/music' : '/movies'

  const sp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (key === 'cat') continue
    if (typeof value === 'string') {
      sp.set(key, value)
    } else if (Array.isArray(value)) {
      value.forEach((v) => sp.append(key, v))
    }
  }

  const qs = sp.toString()
  redirect(qs ? `${target}?${qs}` : target)
}
