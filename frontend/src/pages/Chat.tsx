import { useState } from 'react';
import { api } from '../services/api';
import { useUserStore } from '../stores/userStore';
import { Button, Input, Card } from '../components/ui';
import { Header } from '../components/layout/Navigation';

export default function Chat() {
  const token = useUserStore((s) => s.token);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !input.trim()) return;

    const userMsg = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const result = await api.ai.chat(token, [...messages, userMsg]);
      setMessages((prev) => [...prev, { role: 'assistant', content: result.response }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I couldn\'t process that request.' }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background pb-20 flex flex-col">
      <Header title="AI Chat" />
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && (
          <Card className="text-center py-8">
            <div className="text-text-tertiary">Ask me anything about your tasks, goals, or patterns.</div>
          </Card>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
              msg.role === 'user'
                ? 'bg-secondary text-white rounded-br-md'
                : 'bg-surface text-text-primary rounded-bl-md'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface rounded-2xl rounded-bl-md px-4 py-2.5 text-sm text-text-tertiary">
              Thinking...
            </div>
          </div>
        )}
      </div>
      <form onSubmit={handleSend} className="border-t border-default bg-background p-3 flex gap-2">
        <Input
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" disabled={loading || !input.trim()}>Send</Button>
      </form>
    </div>
  );
}
