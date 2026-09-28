function StatCard({ title, value, description, icon }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">

      <div className="flex items-start justify-between">

        <div>
          <p className="text-sm text-slate-500">
            {title}
          </p>

          <h3 className="text-3xl font-bold text-slate-800 mt-2">
            {value}
          </h3>

          <p className="text-xs text-slate-500 mt-2">
            {description}
          </p>
        </div>

        <div className="w-11 h-11 rounded-lg bg-slate-100 flex items-center justify-center text-xl">
          {icon}
        </div>

      </div>

    </div>
  )
}

export default StatCard