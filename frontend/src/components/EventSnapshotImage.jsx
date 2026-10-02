import React, { useState, useEffect } from 'react';
import { ImageOff } from 'lucide-react';

export default function EventSnapshotImage({ 
  src, 
  alt = "Snapshot", 
  className = "", 
  containerClassName = "",
  onClick, 
  showPlaceholderDetails = true 
}) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    setHasError(false);
  }, [src]);

  if (!src || hasError) {
    return (
      <div 
        className={`flex flex-col items-center justify-center bg-slate-900/90 border border-slate-800/80 text-slate-400 p-2 rounded text-center select-none ${containerClassName || className}`}
        title="Snapshot unavailable on this device"
        onClick={onClick}
      >
        <ImageOff className="h-5 w-5 mb-1 text-slate-500 shrink-0" />
        <span className="text-xs font-semibold text-slate-300 leading-tight">Snapshot unavailable</span>
        {showPlaceholderDetails && (
          <span className="text-[10px] text-slate-500 mt-1 leading-tight max-w-[200px]">
            This snapshot is not available on this device.
          </span>
        )}
      </div>
    );
  }

  return (
    <img 
      src={src} 
      alt={alt} 
      className={className} 
      onClick={onClick} 
      onError={() => {
        setHasError(true);
      }} 
    />
  );
}

