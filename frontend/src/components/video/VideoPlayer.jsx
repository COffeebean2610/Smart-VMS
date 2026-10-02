import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Maximize, RotateCcw } from 'lucide-react';
import { Button } from '../ui/button';

export default function VideoPlayer({ url, events = [], autoSeekTime = 0, onTimeUpdate }) {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    console.log("[VideoPlayer] Mounting with URL:", url);
    if (videoRef.current) {
      if (autoSeekTime > 0) {
        videoRef.current.currentTime = autoSeekTime;
      }
      videoRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.log("[VideoPlayer] Autoplay prevented by browser policy:", err);
        setIsPlaying(false);
      });
    }
  }, [url, autoSeekTime]);

  const handleVideoError = (e) => {
    const video = e.target;
    console.error("[VideoPlayer] Error loading video:");
    console.error("  URL:", url);
    console.error("  Error Code:", video.error ? video.error.code : "Unknown");
    console.error("  Error Message:", video.error ? video.error.message : "No message");
    console.error("  Network State:", video.networkState);
    console.error("  Ready State:", video.readyState);
  };

  const handleCanPlay = () => {
    console.log("[VideoPlayer] onCanPlay triggered. Ready State:", videoRef.current?.readyState);
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch(err => {
        console.error("Play error:", err);
      });
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const current = videoRef.current.currentTime;
    const total = videoRef.current.duration;
    if (total > 0) {
      setProgress((current / total) * 100);
    }
    
    if (onTimeUpdate) {
      onTimeUpdate(current);
    }
  };

  const handleLoadedMetadata = () => {
    console.log("[VideoPlayer] onLoadedMetadata triggered. Duration:", videoRef.current?.duration);
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleTimelineClick = (e) => {
    if (!videoRef.current || duration <= 0) return;
    const bounds = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const percentage = x / bounds.width;
    const seekTime = percentage * duration;
    videoRef.current.currentTime = seekTime;
  };

  const handleFullscreen = () => {
    if (videoRef.current?.requestFullscreen) {
      videoRef.current.requestFullscreen();
    }
  };

  const formatTime = (seconds) => {
    if (isNaN(seconds) || seconds < 0) return "00:00";
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="flex flex-col space-y-2 bg-black rounded-lg overflow-hidden border p-2 shadow-lg">
      <div className="relative w-full aspect-video bg-black rounded flex items-center justify-center group cursor-pointer" onClick={togglePlay}>
        <video
          key={url}
          ref={videoRef}
          src={url}
          className="w-full h-full object-contain"
          preload="auto"
          playsInline
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
          onError={handleVideoError}
          onCanPlay={handleCanPlay}
        />
        
        {/* Center Play Button Overlay */}
        {!isPlaying && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <div className="bg-primary text-primary-foreground p-4 rounded-full opacity-80 group-hover:opacity-100 transition shadow-lg">
              <Play className="h-8 w-8 ml-1" />
            </div>
          </div>
        )}
      </div>

      {/* Interactive Timeline with Markers */}
      <div 
        className="relative w-full h-4 bg-secondary rounded cursor-pointer group"
        onClick={handleTimelineClick}
      >
        <div 
          className="absolute top-0 left-0 h-full bg-primary rounded"
          style={{ width: `${progress}%` }}
        />
        
        {/* Event Markers Overlay */}
        {events.map((event, idx) => {
          // Calculate percentage position based on videoTimestamp and duration
          const position = duration > 0 ? (event.videoTimestamp / duration) * 100 : 0;
          return (
            <div 
              key={idx}
              className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-red-500 shadow-sm border border-black/50 hover:scale-150 transition-transform cursor-pointer group/tooltip"
              style={{ left: `calc(${position}% - 4px)` }}
              title={`${event.eventType} - ${formatTime(event.videoTimestamp)}`}
            >
              {/* Tooltip on Hover */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tooltip:block z-50">
                <div className="bg-popover text-popover-foreground text-[10px] px-2 py-1 rounded shadow-lg whitespace-nowrap">
                  {formatTime(event.videoTimestamp)} - {event.eventType}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between text-sm pt-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={togglePlay}>
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { if(videoRef.current) videoRef.current.currentTime = 0; }}>
            <RotateCcw className="h-4 w-4" />
          </Button>
          <span className="font-mono text-xs text-muted-foreground ml-2">
            {formatTime(videoRef.current?.currentTime || 0)} / {formatTime(duration)}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleFullscreen}>
            <Maximize className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
