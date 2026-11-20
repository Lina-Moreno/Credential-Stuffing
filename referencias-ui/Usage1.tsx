import { CircularProgressCard } from "@/components/ui/circular-progress-card";

/**
 * A demo page to showcase the CircularProgressCard component.
 * It demonstrates default usage and customization via props.
 */
const CircularProgressCardDemo = () => {
  return (
    <div className="flex min-h-[500px] w-full flex-wrap items-center justify-center gap-8 bg-background p-4">
      {/* Example: Custom color passed as a prop */}
      <CircularProgressCard
        title="Project Completion"
        description="Tasks completed for the new feature launch."
        currentValue={128}
        goalValue={200}
        currency=""
        progressColor="hsl(142.1 76.2% 41.2%)" // Custom green color
      />
    </div>
  );
};

export default CircularProgressCardDemo;