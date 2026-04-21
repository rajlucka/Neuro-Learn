import { useState } from "react";
import { Rocket, ChevronRight, ChevronLeft, Check } from "lucide-react";
import { diagnosticQuestions } from "@/data/mockData";
import { Button } from "@/components/ui/button";

export function NewStudentView() {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});

  if (!started) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="ai-glow-card p-12 max-w-lg w-full text-center animate-glow-pulse">
          <div className="relative z-10">
            <div className="w-16 h-16 rounded-2xl gradient-ai flex items-center justify-center mx-auto mb-6">
              <Rocket className="h-8 w-8 text-primary-foreground" />
            </div>
            <h1 className="text-3xl font-heading font-bold mb-3">Welcome to Neuro Learn</h1>
            <p className="text-muted-foreground mb-8 leading-relaxed">
              Let's find out where you stand. Take a quick 36-question diagnostic to build your personalized learning path.
            </p>
            <Button
              onClick={() => setStarted(true)}
              className="gradient-ai text-primary-foreground px-8 py-3 text-lg font-semibold rounded-xl hover:opacity-90 transition-opacity"
            >
              <Rocket className="mr-2 h-5 w-5" /> Start Baseline Diagnostic
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const questionsPerStep = 6;
  const totalSteps = 6;
  const currentQuestions = diagnosticQuestions.slice(step * questionsPerStep, (step + 1) * questionsPerStep);
  const isLastStep = step === totalSteps - 1;

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-muted-foreground mb-2">
          <span>Step {step + 1} of {totalSteps}</span>
          <span>{Math.round(((step + 1) / totalSteps) * 100)}%</span>
        </div>
        <div className="h-2 bg-secondary rounded-full overflow-hidden">
          <div className="h-full gradient-ai rounded-full transition-all duration-500" style={{ width: `${((step + 1) / totalSteps) * 100}%` }} />
        </div>
      </div>

      <div className="space-y-6">
        {currentQuestions.map((q) => (
          <div key={q.id} className="glass-card p-5">
            <p className="font-medium mb-3">{q.question}</p>
            <div className="grid grid-cols-2 gap-2">
              {q.options.map((opt, oi) => (
                <button
                  key={oi}
                  onClick={() => setAnswers({ ...answers, [q.id]: oi })}
                  className={`p-3 rounded-lg text-sm text-left transition-all border ${
                    answers[q.id] === oi
                      ? "border-primary bg-primary/5 text-primary font-medium"
                      : "border-border hover:border-primary/30"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between mt-8">
        <Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
          <ChevronLeft className="mr-1 h-4 w-4" /> Previous
        </Button>
        {isLastStep ? (
          <Button className="gradient-ai text-primary-foreground">
            <Check className="mr-1 h-4 w-4" /> Submit
          </Button>
        ) : (
          <Button onClick={() => setStep(step + 1)}>
            Next <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
