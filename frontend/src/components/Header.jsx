function Header() {
  return (
    <header className="flex min-h-16 items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 pl-16 sm:px-6 md:pl-6 lg:px-8">
      <div className="min-w-0">
        <h2 className="truncate text-base font-semibold text-slate-800 sm:text-lg">
          Hospital Operations Dashboard
        </h2>
        <p className="truncate text-xs text-slate-500 sm:text-sm">
          Real-time hospital intelligence
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium text-slate-700">
            Hospital Administrator
          </p>
          <p className="text-xs text-slate-500">Operations</p>
        </div>

        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-sm font-semibold text-white">
          HA
        </div>
      </div>
    </header>
  )
}

export default Header
