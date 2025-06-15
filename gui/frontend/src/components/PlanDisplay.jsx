import React from 'react';

const PlanDisplay = ({ plan }) => {
  if (!plan || !plan.steps || plan.steps.length === 0) {
    // You can return null or a placeholder if there's no plan or no steps
    // For now, let's return a minimal message if plan object exists but is empty.
    if (plan && (!plan.steps || plan.steps.length === 0) && plan.title) {
         return (
            <div className="p-3 bg-gray-700 text-gray-300 text-sm border-b border-gray-600 shrink-0">
                <h3 className="font-semibold text-gray-100">{plan.title || "Plan"}</h3>
                <p>No steps defined in the plan yet.</p>
            </div>
        );
    }
    return null; 
  }

  return (
    <div className="p-3 bg-gray-700 text-gray-300 text-sm border-b border-gray-600 shrink-0 max-h-64 overflow-y-auto"> {/* Added max-h and overflow */}
      <h3 className="font-semibold text-lg text-gray-100 mb-2">{plan.title || "Current Plan"}</h3>
      <div className="mb-2">
        <span>Progress: {plan.completed_steps || 0}/{plan.total_steps || 0} steps completed ({plan.progress_percent || '0%'})</span>
      </div>
      <ul className="list-none space-y-1">
        {plan.steps.map((step, index) => (
          <li key={index} className="flex items-start p-1 rounded bg-gray-600/50">
            <span className="mr-2 w-5 text-center">{step.status_icon || (step.status === 'completed' ? '✅' : step.status === 'in_progress' ? '⏳' : step.status === 'blocked' ? '❌' : '📋')}</span>
            <span className="flex-grow">{step.text}</span>
            {step.notes && <span className="ml-2 text-xs text-gray-400 italic">(Notes: {step.notes})</span>}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PlanDisplay;
