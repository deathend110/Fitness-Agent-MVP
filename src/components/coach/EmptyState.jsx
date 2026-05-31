import { getCoachEmptyQuestionView } from '../../utils/coachView.js'

function EmptyState({ onSuggestionClick, questions = getCoachEmptyQuestionView() }) {
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col items-center text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border-2 border-fitloop-orange/20 bg-fitloop-orange/10 text-xl font-black text-fitloop-orange">
        R
      </div>

      <h1 className="mb-2 text-2xl font-bold text-slate-800">
        Hello, I&apos;m <span className="text-fitloop-orange">RepMind</span>
      </h1>
      <p className="mb-8 text-sm leading-6 text-slate-500">
        基于你的档案、训练计划和今日数据，为你提供专业健身建议。
      </p>

      <div className="grid w-full gap-2.5 md:grid-cols-2">
        {questions.map((item) => (
          <button
            className="rounded-xl border border-fitloop-line bg-white p-3.5 text-left text-sm leading-5 text-slate-700 transition hover:border-fitloop-orange/30 hover:bg-fitloop-orange/5 hover:shadow-sm"
            key={item.id}
            onClick={() => onSuggestionClick?.(item.text)}
            type="button"
          >
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-fitloop-orange">
              {item.label}
            </span>
            {item.text}
          </button>
        ))}
      </div>
    </div>
  )
}

export default EmptyState
