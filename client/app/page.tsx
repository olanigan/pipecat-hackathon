"use client";

import {
  PipecatClientAudio,
  usePipecatClient,
  useRTVIClientEvent,
} from "@pipecat-ai/client-react";
import { RTVIEvent } from "@pipecat-ai/client-js";
import clsx from "clsx";
import { useEffect, useState, useCallback, useRef } from "react";

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function Home() {
  const pipecatClient = usePipecatClient();
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Welcome to AI Copilot Assistant

I'm here to help with:
• AI news and research updates
• ArXiv paper searches
• HuggingFace model discovery
• Latest AI developments

Start speaking or type your questions below!`,
      timestamp: new Date(),
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const isConnectingRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Listen for bot speaking events to detect speaking state
  useRTVIClientEvent(
    RTVIEvent.UserStartedSpeaking,
    useCallback(() => {
      setIsSpeaking(true);
    }, [])
  );

  useRTVIClientEvent(
    RTVIEvent.UserStoppedSpeaking,
    useCallback(() => {
      setIsSpeaking(false);
    }, [])
  );

  // Listen for conversation messages
  useRTVIClientEvent(
    RTVIEvent.UserTranscript,
    useCallback((transcript: any) => {
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: transcript.text || transcript,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, userMessage]);
    }, [])
  );

  useRTVIClientEvent(
    RTVIEvent.BotTranscript,
    useCallback((transcript: any) => {
      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: transcript.text || transcript,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, botMessage]);
    }, [])
  );

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle text input submission
  const handleSendMessage = useCallback(async () => {
    if (!inputText.trim() || isSending || !pipecatClient?.connected) return;

    setIsSending(true);
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputText('');

    try {
      // Send the text to the bot via Pipecat client
      await pipecatClient.sendText(inputText.trim());
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error sending your message. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  }, [inputText, isSending, pipecatClient]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  useEffect(() => {
    if (!pipecatClient || isConnectingRef.current || pipecatClient.connected) return;

    const startConnection = async () => {
      try {
        isConnectingRef.current = true;
        await pipecatClient.startBotAndConnect({
          endpoint: `${
            process.env.NEXT_PUBLIC_PIPECAT_API_URL || "/api"
          }/connect`,
        });
      } catch (error) {
        console.error("Failed to start connection:", error);
      } finally {
        isConnectingRef.current = false;
      }
    };

    startConnection();

    return () => {
      if (pipecatClient.connected) {
        pipecatClient.disconnect();
      }
      isConnectingRef.current = false;
    };
  }, [pipecatClient]);

  return (
    <div className="h-screen flex bg-gray-50 dark:bg-gray-900">
      {/* Voice Panel Sidebar - Fixed */}
      <div className="w-96 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col items-center justify-center relative p-8 shadow-lg">
        <div className="text-center space-y-6">
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              AI Copilot Voice
            </h2>
            <div className="text-neutral-600 dark:text-neutral-400 space-y-3">
              <p className="text-sm font-medium">
                Powered by:
              </p>
              <ul className="text-xs space-y-2">
                <li className="flex items-center justify-center space-x-2">
                  <A href="https://pipecat.ai">Pipecat</A>
                  <span className="text-neutral-400">•</span>
                  <A href="https://daily.co">Daily</A>
                </li>
                <li className="flex items-center justify-center space-x-2">
                  <A href="https://www.cartesia.ai/">Cartesia</A>
                  <span className="text-neutral-400">•</span>
                  <A href="https://nextjs.org">Next.js</A>
                </li>
              </ul>
            </div>

            <div className="text-xs text-neutral-500 dark:text-neutral-400 text-center bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
              <p className="font-medium mb-1">Voice Controls</p>
              <p>Start speaking or say "stop" to interrupt</p>
              <p className="mt-2 text-blue-600 dark:text-blue-400">💬 Use text input below too!</p>
            </div>
          </div>

          {/* Animated voice indicator */}
          <div className="relative">
            <div
              className={clsx(
                "size-40 blur-2xl rounded-full bg-gradient-to-b from-blue-400 to-purple-600 dark:from-blue-500 dark:to-purple-700 transition-all duration-300 ease-in-out",
                {
                  "opacity-30": !isSpeaking,
                  "opacity-100 scale-110 animate-pulse": isSpeaking,
                }
              )}
            />
            {isSpeaking && (
              <div className="absolute inset-0 size-32 blur-xl rounded-full bg-gradient-to-b from-cyan-300 to-blue-500 dark:from-cyan-400 dark:to-blue-600 opacity-60 animate-ping m-auto" />
            )}
            
            {/* Status indicator */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className={clsx(
                "size-16 rounded-full flex items-center justify-center text-white font-bold text-sm backdrop-blur-sm",
                isSpeaking 
                  ? "bg-red-500 animate-pulse" 
                  : "bg-gray-600 dark:bg-gray-700"
              )}>
                {isSpeaking ? "🎤" : "🤖"}
              </div>
            </div>
          </div>

          <PipecatClientAudio />
        </div>
      </div>

      {/* Chat Area - Scrollable with fixed container */}
      <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
        {/* Chat Header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 shadow-sm">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            AI Copilot Assistant
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Your AI assistant for research, news, and model discovery
          </p>
        </div>

        {/* Messages Area - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={clsx(
                  "flex",
                  message.role === 'user' ? "justify-end" : "justify-start"
                )}
              >
                <div
                  className={clsx(
                    "max-w-2xl rounded-2xl px-4 py-3 shadow-sm",
                    message.role === 'user'
                      ? "bg-blue-600 text-white ml-auto"
                      : "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700"
                  )}
                >
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </div>
                  <div className={clsx(
                    "text-xs mt-2 opacity-70",
                    message.role === 'user' ? "text-blue-100" : "text-gray-500 dark:text-gray-400"
                  )}>
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Text Input Area - Fixed at bottom */}
        <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4 shadow-lg">
          <div className="max-w-4xl mx-auto">
            <div className="flex space-x-3">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message here... (Press Enter to send)"
                disabled={isSending}
                className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputText.trim() || isSending}
                className={clsx(
                  "px-6 py-3 rounded-lg font-medium transition-all duration-200",
                  "bg-blue-600 hover:bg-blue-700 text-white",
                  "disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed",
                  "shadow-sm hover:shadow-md"
                )}
              >
                {isSending ? (
                  <span className="flex items-center space-x-2">
                    <span className="animate-pulse">⏳</span>
                    <span>Sending...</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-2">
                    <span>Send</span>
                    <span>📤</span>
                  </span>
                )}
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
              💡 Tip: You can speak directly or type messages. Both work seamlessly!
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function A(props: React.ComponentPropsWithoutRef<"a">) {
  return (
    <a
      {...props}
      className="font-extrabold hover:underline"
    />
  );
}
