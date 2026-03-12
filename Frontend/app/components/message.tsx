'use client'

import { Bot, User, Volume2, Square, Loader2 } from "lucide-react"
import { cn } from "@/app/lib/utils"
import { memo } from "react"

interface MessageProps {
  id?: string
  content: string
  role: "doctor" | "patient"
  timestamp: Date
  isTyping?: boolean
  isWaiting?: boolean
  audioBlobUrl?: string
  status?: "recording" | "uploading" | "thinking" | "audio_loading" | "audio_playing"
  isPlaying?: boolean
}

export const Message = memo(function Message({
  id,
  content,
  role,
  timestamp,
  isTyping,
  isWaiting,
  audioBlobUrl,
  status,
  isPlaying
}: MessageProps) {
  const isDoctor = role === "doctor"

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat("zh-CN", {
      hour: "numeric",
      minute: "numeric",
      hourCycle: 'h12'
    }).format(date)
  }

  return (
    <div className={cn(
      "flex items-end gap-3 mb-6 group",
      isDoctor ? "flex-row" : "flex-row-reverse"
    )}>
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
        isDoctor 
          ? "bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400"
          : "bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"
      )}>
        {isDoctor ? (
          <Bot className="w-5 h-5" aria-label="医生" />
        ) : (
          <User className="w-5 h-5" aria-label="患者" />
        )}
      </div>

      <div className="flex flex-col gap-1 max-w-[85%] sm:max-w-[70%]">
        <div className={cn(
          "rounded-2xl px-4 py-2.5 text-sm shadow-sm transition-colors",
          isDoctor
            ? "bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-200"
            : "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
          isTyping && "min-w-[60px]"
        )}>
          {isTyping ? (
            <div className="flex gap-1 items-center h-6 px-2">
              {[0.3, 0.15, 0].map((delay) => (
                <span 
                  key={delay}
                  className="w-2 h-2 rounded-full bg-current animate-bounce"
                  style={{ animationDelay: `-${delay}s` }}
                />
              ))}
            </div>
          ) : (
            <span dangerouslySetInnerHTML={{ __html: content }} />
          )}
        </div>
        
        <span className={cn(
          "text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity",
          isDoctor ? "text-left" : "text-right"
        )}>
          {formatTime(timestamp)}
        </span>
      </div>
    </div>
  )
})