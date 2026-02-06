'use client'

import React, { useEffect, useRef, useState } from "react"
import { ScrollArea } from "@/app/components/ui/scroll-area"
import { Button } from "@/app/components/ui/button"
import { Message } from "@/app/components/message"
import { Mic, Square, Users, Send, RefreshCw, FileText, Volume2, Loader2 } from "lucide-react"
import { v4 as uuidv4 } from 'uuid'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Markdown } from 'tiptap-markdown'
import { API_BASE_URL, WS_BASE_URL, WS_TTS_URL } from "@/lib/env"
import { cn } from "@/app/lib/utils"

interface ChatMessage {
  id: string
  content: string
  role: "doctor" | "patient"
  timestamp: Date
  isTyping?: boolean
  status?: "recording" | "uploading" | "thinking" | "audio_loading" | "audio_playing"
  audioBlobUrl?: string
}

export default function PreDiagnosisPage() {
  const [mounted, setMounted] = useState(false)
  const [sessionId, setSessionId] = useState(uuidv4())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [isFinished, setIsFinished] = useState(false)
  const audioContextRef = useRef<AudioContext | null>(null)
  const audioSourceRef = useRef<HTMLAudioElement | null>(null)
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string | null>(null)

  const editor = useEditor({
    extensions: [
      StarterKit,
      Markdown.configure({
        html: false,
        tightLists: true,
      })
    ],
    content: '',
    editable: false,
    editorProps: {
      attributes: {
        class: 'prose focus:outline-none',
      },
    },
  })

  useEffect(() => {
    setMounted(true)
    return () => {
      editor?.destroy()
      audioSourceRef.current?.pause()
    audioSourceRef.current = null
      audioContextRef.current?.close()
    }
  }, [editor])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto"
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`
    }
  }, [input])

  const playAudio = async (messageId: string, audioBlobUrl: string) => {
    if (currentlyPlaying === messageId) {
      audioSourceRef.current?.pause()
      audioSourceRef.current = null
      setCurrentlyPlaying(null)
      return
    }

    try {
      if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
      }

      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume()
      }

      audioSourceRef.current?.pause()
    audioSourceRef.current = null
      setCurrentlyPlaying(messageId)

      // 直接使用 HTML5 Audio 播放 MP3
      const audio = new Audio(audioBlobUrl)
      audio.onended = () => {
        setCurrentlyPlaying(null)
      }
      audio.onerror = (error) => {
        console.error('音频播放错误:', error)
        setCurrentlyPlaying(null)
      }
      audio.play()
      audioSourceRef.current = audio as any

    } catch (error) {
      console.error('播放失败:', error)
      setCurrentlyPlaying(null)
    }
  }

  const fetchTextToSpeech = async (text: string, messageId: string) => {
    setMessages(prev => prev.map(msg =>
      msg.id === messageId
        ? { ...msg, status: "audio_loading" }
        : msg
    ))

    try {
      const ws = new WebSocket(`${WS_TTS_URL}/ws/tts`)
      const audioChunks: Uint8Array[] = []

      ws.onopen = () => {
        console.log('[TTS] 开始语音合成')
        // 发送JSON格式的配置
        ws.send(JSON.stringify({
          text: text,
          voice_name: "xiaoyan",
          speed: 50,
          volume: 50,
          pitch: 50,
          audio_format: "lame"
        }))
      }

      ws.onmessage = async (event) => {
        // 处理二进制音频数据
        if (event.data instanceof Blob) {
          const arrayBuffer = await event.data.arrayBuffer()
          audioChunks.push(new Uint8Array(arrayBuffer))
        }
        // 处理JSON状态消息
        else {
          try {
            const data = JSON.parse(event.data)
            console.log('[TTS] 状态消息:', data)

            if (data.type === 'complete') {
              console.log('[TTS] 语音合成完成，音频块数量:', audioChunks.length)

              if (audioChunks.length > 0) {
                // 合并所有音频块
                const totalLength = audioChunks.reduce((sum, chunk) => sum + chunk.length, 0)
                const combinedArray = new Uint8Array(totalLength)
                let offset = 0
                for (const chunk of audioChunks) {
                  combinedArray.set(chunk, offset)
                  offset += chunk.length
                }

                // 创建 Blob 和 URL（mp3 格式）
                const combinedBlob = new Blob([combinedArray], { type: 'audio/mpeg' })
                const audioUrl = URL.createObjectURL(combinedBlob)

                setMessages(prev => prev.map(msg =>
                  msg.id === messageId
                    ? { ...msg, audioBlobUrl: audioUrl, status: undefined }
                    : msg
                ))
              } else {
                console.warn('[TTS] 没有收到音频数据')
                setMessages(prev => prev.map(msg =>
                  msg.id === messageId
                    ? { ...msg, status: undefined }
                    : msg
                ))
              }
              ws.close()
            } else if (data.type === 'error') {
              console.error('[TTS] 错误:', data.message)
              setMessages(prev => prev.map(msg =>
                msg.id === messageId
                  ? { ...msg, status: undefined }
                  : msg
              ))
              ws.close()
            }
          } catch (e) {
            // 不是JSON，忽略
          }
        }
      }

      ws.onerror = (error) => {
        console.error('[TTS] WebSocket错误:', error)
        setMessages(prev => prev.map(msg =>
          msg.id === messageId
            ? { ...msg, status: undefined }
            : msg
        ))
      }

      ws.onclose = () => {
        console.log('[TTS] WebSocket已关闭')
      }
    } catch (error) {
      console.error('[TTS] 初始化失败:', error)
      setMessages(prev => prev.map(msg =>
        msg.id === messageId
          ? { ...msg, status: undefined }
          : msg
      ))
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmitMessage()
    }
  }

  const handleSubmitMessage = () => {
    if (input.trim()) {
      handleSubmit(input)
      setInput("")
    }
  }

  const resetConversation = () => {
    if (isRecording && mediaRecorder) {
      mediaRecorder.stop()
      mediaRecorder.stream?.getTracks().forEach(track => track.stop())
    }
    
    audioSourceRef.current?.pause()
    audioSourceRef.current = null
    setCurrentlyPlaying(null)
    
    setSessionId(uuidv4())
    setMessages([])
    setInput("")
    setIsRecording(false)
    setIsFinished(false)
    editor?.commands.setContent("")
    setMediaRecorder(null)
  }

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorder?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioChunks: Blob[] = [];
      
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      
      recorder.ondataavailable = (e) => {
        audioChunks.push(e.data);
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        
        const ws = new WebSocket(`${WS_BASE_URL}/audio/upload`);
        
        ws.onopen = async () => {
          console.log(`[DEBUG] WebSocket连接已建立，正在发送音频数据...`);
          const arrayBuffer = await audioBlob.arrayBuffer();
          ws.send(arrayBuffer);
        };

        // 用于保存最长的识别结果
        let longestText = "";

        ws.onmessage = (event) => {
          const result = event.data;
          console.log("[DEBUG] 前端收到消息:", result, "类型:", typeof result, "长度:", result.length);

          if (result === "END") {
            console.log("[DEBUG] 收到END，关闭连接");
            ws.close();
            return;
          }

          // 跳过JSON消息（ready、error等），只处理识别文字
          if (result.startsWith("{") || result.includes("type")) {
            console.log("[DEBUG] 跳过JSON消息:", result);
            return;
          }

          // 保留最长的结果（因为讯飞返回的是累积结果）
          if (result.length > longestText.length) {
            longestText = result;
            console.log("[DEBUG] 更新输入框，之前:", input, "现在:", longestText);
            setInput(longestText);
            console.log("[DEBUG] 更新后的input值:", input); // 立即检查
          } else {
            console.log("[DEBUG] 结果太短，不更新。当前最长:", longestText, "收到:", result);
          }
        };
        
        ws.onerror = (error) => {
          console.error("[DEBUG] WebSocket错误:", error);
          ws.close();
        };
        
        ws.onclose = () => {
          console.log("[DEBUG] WebSocket连接已关闭");
          stream.getTracks().forEach(track => track.stop());
        };
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      console.error("[DEBUG] 录音处理失败:", err);
    }
  };

  const handleSubmit = async (content: string) => {
    if (!content.trim()) return;
  
    const newMessage: ChatMessage = {
      id: uuidv4(),
      content,
      role: "patient",
      timestamp: new Date(),
    };
  
    setMessages(prev => [...prev, newMessage]);
  
    const thinkingMessageId = uuidv4();
    setMessages(prev => [...prev, {
      id: thinkingMessageId,
      content: "医生正在思考中...",
      role: "doctor",
      timestamp: new Date(),
      status: "thinking"
    }]);
  
    try {
      const requestBody = {
        session_id: sessionId,
        patient_content: content
      };

      const preDiagnosisUrl = `${API_BASE_URL}/api/chat`;
      
      console.log("[DEBUG] 正在发送消息到后端...");
      console.log(`[DEBUG] 请求URL: ${preDiagnosisUrl}`);
      console.log("[DEBUG] 请求参数:", requestBody);

      const response = await fetch(preDiagnosisUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        console.error("[DEBUG] 请求失败，状态码:", response.status);
        throw new Error(`请求失败: ${response.status}`);
      }
  
      const responseInfo = await response.json();
      console.log("[DEBUG] 收到医生回复:", responseInfo);

      // 使用后端返回的 is_completed 字段来判断是否完成
      const diagnosisFinished = responseInfo.is_completed === true;

      setMessages(prev => {
        const filtered = prev.filter(msg => msg.id !== thinkingMessageId);

        if (diagnosisFinished) {
          console.log("[DEBUG] 诊断已完成，移除思考中消息");
          return filtered;
        }

        const doctorMessage: ChatMessage = {
          id: thinkingMessageId,
          content: responseInfo.worker_inquiry,
          role: "doctor",
          timestamp: new Date()
        };

        console.log("[DEBUG] 添加医生回复:", doctorMessage);

        return [...filtered, doctorMessage];
      });

      if (!diagnosisFinished && responseInfo.worker_inquiry) {
        await fetchTextToSpeech(responseInfo.worker_inquiry, thinkingMessageId);
      }

      if (diagnosisFinished) {
        console.log("[DEBUG] 标记诊断已完成");
        setIsFinished(true);
      }
  
    } catch (error) {
      console.error('[DEBUG] 消息处理失败:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === thinkingMessageId 
          ? { ...msg, content: "医生回复获取失败，请稍后再试", status: undefined }
          : msg
      ));
    }
  };

  const generateSummary = async () => {
    if (!isFinished || !editor) return;
  
    const reportUrl = `${API_BASE_URL}/dialogue/report?session_id=${sessionId}`;
    
    console.log("[DEBUG] 正在请求报告数据...");
    console.log("[DEBUG] Session ID:", sessionId);
    console.log(`[DEBUG] 请求URL: ${reportUrl}`);
  
    try {
      const response = await fetch(reportUrl);
      
      if (!response.ok) {
        console.error("[DEBUG] 请求失败，状态码:", response.status);
        throw new Error("后端无响应");
      }
      
      const reportData = await response.json();
      console.log("[DEBUG] 报告数据完整响应:", reportData);
  
      const markdownReport = `
### 电子预问诊报告
**生成时间**：${new Date().toLocaleDateString()}  
**就诊编号**：${sessionId.slice(0, 8).toUpperCase()}

---

#### 主要症状记录
${reportData.chief_complaint || "无记录"}

#### 病史
${reportData.history_of_present_illness || "无记录"}

#### 既往史
${reportData.past_history || "无记录"}

#### 过敏史
${reportData.allergy_history || "无记录"}

#### 家族史
${reportData.family_history || "无记录"}

---
      `.trim();
  
      console.log("[DEBUG] 生成的Markdown报告:", markdownReport);
      editor.commands.setContent(markdownReport);
    } catch (error) {
      console.error("[DEBUG] 生成报告失败:", error);
      editor.commands.setContent("## 报告生成失败\n请稍后重试");
    }
  };

  return (
    <div className="flex h-screen flex-col bg-gradient-to-br from-blue-50/60 to-emerald-50/60 dark:from-gray-950 dark:to-gray-950">
      <div className="bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:bg-gray-950/90 p-4 sticky top-0 z-10 shadow-lg rounded-b-xl">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-emerald-600 bg-clip-text text-transparent">
              MedSynthAi
            </h1>
            <div className="flex items-center text-base text-muted-foreground">
              <Users className="mr-2 h-5 w-5" />
              <span>会话ID: {sessionId.slice(0, 8)}...</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Button 
              variant="outline" 
              size="lg"
              className="rounded-xl h-11 w-11 hover:scale-105 transition-transform"
              onClick={resetConversation}
            >
              <RefreshCw className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>
  
      <div className="flex-1 flex overflow-hidden px-4 pb-4">
        <div className="flex-1 overflow-hidden pr-4">
          <ScrollArea className="h-[calc(100vh-180px)] rounded-xl shadow-inner">
            <div className="max-w-3xl mx-auto p-4 space-y-6">
              {messages.map((message) => (
                <div 
                  key={message.id}
                  className={cn(
                    "flex items-end gap-3 mb-6 group",
                    message.role === "doctor" ? "flex-row" : "flex-row-reverse"
                  )}
                >
                  {message.role === "doctor" && message.audioBlobUrl && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => playAudio(message.id, message.audioBlobUrl!)}
                      disabled={message.status === "audio_loading"}
                      className={message.role === "doctor" ? "mr-2" : "ml-2"}
                    >
                      {currentlyPlaying === message.id ? (
                        <Square className="h-4 w-4" />
                      ) : (
                        <Volume2 className="h-4 w-4" />
                      )}
                      {message.status === "audio_loading" && (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      )}
                    </Button>
                  )}
                  <Message
                    key={message.id}
                    content={message.content}
                    role={message.role}
                    timestamp={message.timestamp}
                    isTyping={message.isTyping || message.status === "thinking"}
                  />
                </div>
              ))}
              <div ref={scrollRef} />
            </div>
          </ScrollArea>
        </div>
  
        <div className="w-1/3 border-l-2 border-gray-200 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:border-gray-800 dark:bg-gray-950/90 p-6 shadow-xl rounded-xl flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-blue-600 dark:text-blue-400">
              问诊报告
            </h2>
            <div className="flex flex-col items-end">
              <Button 
                variant="outline" 
                size="sm"
                className="rounded-xl h-10 w-10 hover:scale-105 transition-transform"
                onClick={generateSummary}
                disabled={!isFinished}
              >
                <FileText className="h-5 w-5" />
              </Button>
              {isFinished && (
                <span className="text-xs text-muted-foreground mt-1">
                  对话已结束，请点击按钮生成报告
                </span>
              )}
            </div>
          </div>
          {mounted && (
            <ScrollArea className="flex-1 rounded-lg border border-gray-200 dark:border-gray-700">
              <EditorContent 
                editor={editor} 
                className="prose prose-base max-w-none dark:prose-invert prose-headings:text-gray-800 
                         dark:prose-headings:text-gray-200 prose-strong:text-blue-600 prose-ul:mt-4 
                         prose-li:mt-2 prose-p:leading-relaxed prose-p:text-gray-700 
                         dark:prose-p:text-gray-300 p-4 bg-gray-50/50 dark:bg-gray-900/50"
              />
            </ScrollArea>
          )}
        </div>
      </div>
  
      <div className="border-t bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:bg-gray-950/90 p-4 sticky bottom-0 shadow-2xl rounded-t-xl">
        <div className="max-w-6xl mx-auto flex gap-3 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="请详细描述您的症状...(按Enter发送，Shift+Enter换行)"
              className="w-full h-14 min-h-[56px] max-h-[200px] text-lg font-medium leading-relaxed rounded-xl shadow-sm 
                       focus-visible:ring-2 focus-visible:ring-blue-500 border-2 
                       border-gray-200 dark:border-gray-700 focus:border-blue-500 
                       dark:focus:border-blue-500 pl-6 pr-6 placeholder:text-gray-500 
                       placeholder:text-base/[30px] placeholder:font-normal py-4 resize-none"
              rows={1}
              style={{ overflowY: 'auto' }}
            />
          </div>
          <div className="flex gap-3">
            <Button
              type="button"
              variant={isRecording ? "destructive" : "outline"}
              size="lg"
              className="rounded-xl h-14 w-14 transition-all duration-300 scale-100 hover:scale-105"
              onClick={toggleRecording}
            >
              {isRecording ? (
                <Square className="h-6 w-6 animate-pulse" />
              ) : (
                <Mic className="h-6 w-6" />
              )}
            </Button>
            <Button 
              type="button" 
              size="lg"
              className="rounded-xl h-14 px-8 text-lg font-medium bg-blue-600 hover:bg-blue-700 
                       text-white shadow-lg transition-all hover:scale-105"
              onClick={handleSubmitMessage}
              disabled={messages.some(msg => msg.isTyping || msg.status === "thinking")}
            >
              <Send className="h-6 w-6 mr-2" />
              发送
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}