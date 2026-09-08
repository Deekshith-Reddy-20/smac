export type AskContext = {
  transcript?: string;
  system?: string;
  ephemeral?: string;
};

export type InterviewAnswerBlock = {
  direct: string;
  explanation: string;
  example: string;
  interview_answer: string;
};

export type InterviewAnswerResponse = {
  success: boolean;
  status?: "answer" | "skip" | "unclear" | string;
  is_question: boolean;
  question_complete?: boolean;
  question: string;
  category: string;
  answer?: InterviewAnswerBlock | null;
  example?: string;
  confidence?: number;
  error?: string;
};

export type ChatResponse = {
  success: boolean;
  answer?: string;
  error?: string;
};

export type TranscribeResponse = {
  success: boolean;
  text?: string;
  source?: string;
  error?: string;
};

export type TranslateResponse = {
  success: boolean;
  translated_text?: string;
  error?: string;
};

export type ActionItem = {
  task: string;
  priority: "high" | "medium" | "low" | string;
};

export type ActionsResponse = {
  success: boolean;
  actions?: ActionItem[];
  error?: string;
};

export type TranscriptLine = {
  id: string;
  source: "mic" | "system" | "typed";
  text: string;
};

export type ChatMessage = {
  id: string;
  role: "interviewer" | "savuor";
  content: string;
  timestamp: string;
  category?: string;
  confidence?: number;
  pending?: boolean;
};

export type ResumeUploadResponse = {
  success: boolean;
  filename?: string;
  characters?: number;
  message?: string;
  error?: string;
};
