export function StorageProgressChart({ used, total = "2.0 TB" }) {
  // Dummy logic for width %
  const percentage = 60;
  
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Used: {used}</span>
        <span className="text-muted-foreground">Total: {total}</span>
      </div>
      <div className="h-4 w-full overflow-hidden rounded-full bg-secondary">
        <div 
          className="h-full bg-primary transition-all duration-500 ease-in-out" 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-right text-xs text-muted-foreground">
        {percentage}% Capacity Reached
      </div>
    </div>
  );
}
