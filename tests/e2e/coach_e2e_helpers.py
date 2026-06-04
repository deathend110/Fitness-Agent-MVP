import json
import os
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_HOST = "127.0.0.1"
APP_PORT = 5173
APP_URL = f"http://{APP_HOST}:{APP_PORT}"


def _is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def wait_for_app_ready(app_url=APP_URL, timeout_seconds=45):
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with urlopen(app_url, timeout=1.5) as response:
                if response.status < 500:
                    return
        except Exception as error:  # pragma: no cover
            last_error = error
            time.sleep(0.5)

    raise RuntimeError(f"等待前端开发服务器启动超时：{app_url}；最后错误：{last_error}")


@contextmanager
def ensure_vite_dev_server(app_url=APP_URL):
    # E2E 统一自举前端，避免依赖手工先启动 5173 导致验证不可复现。
    if _is_port_open(APP_HOST, APP_PORT):
        wait_for_app_ready(app_url)
        yield app_url
        return

    npm_executable = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_executable:
        raise RuntimeError("未找到 npm，无法自动启动 Vite 开发服务器。")

    process = subprocess.Popen(
        [
            npm_executable,
            "run",
            "dev",
            "--",
            "--host",
            APP_HOST,
            "--port",
            str(APP_PORT),
            "--strictPort",
        ],
        cwd=ROOT_DIR,
        env={**os.environ},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_app_ready(app_url)
        yield app_url
    finally:
        if process.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:  # pragma: no cover
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


def install_coach_backend_fetch_mock(context, config):
    # 在页面内接管 /api fetch，让流式分块、消息持久化和切页回页共用同一份状态。
    context.add_init_script(
        """
        (() => {
          const mockConfig = %s;
          const nativeFetch = window.fetch.bind(window);
          const encoder = new TextEncoder();
          const jsonClone = (value) => JSON.parse(JSON.stringify(value ?? null));

          const state = {
            profile: jsonClone(mockConfig.profile),
            weeklyPlan: jsonClone(mockConfig.weeklyPlan),
            dailyLog: jsonClone(mockConfig.dailyLog ?? {}),
            models: jsonClone(mockConfig.models),
            modelConfig: jsonClone(mockConfig.modelConfig ?? null),
            defaultSession: jsonClone(mockConfig.defaultSession),
            sessions: jsonClone(mockConfig.sessions ?? []),
            messagesBySession: jsonClone(mockConfig.messagesBySession ?? {}),
            draftsBySession: jsonClone(mockConfig.draftsBySession ?? {}),
            streamScenarios: jsonClone(mockConfig.streamScenarios ?? []),
            replyScenarios: jsonClone(mockConfig.replyScenarios ?? []),
            backgroundTasks: jsonClone(mockConfig.backgroundTasks ?? {}),
            commitResult: jsonClone(mockConfig.commitResult ?? null),
            commitCalls: [],
            ignoreCalls: [],
            replyCalls: [],
            streamCalls: [],
            eventLog: [],
            nextMessageId: Number.isFinite(mockConfig.nextMessageId) ? mockConfig.nextMessageId : 1000,
          };

          window.__coachMockState = state;

          function jsonResponse(payload, status = 200) {
            return new Response(JSON.stringify(payload), {
              status,
              headers: { 'Content-Type': 'application/json' },
            });
          }

          function parseBody(init = {}) {
            if (typeof init.body !== 'string') {
              return null;
            }

            try {
              return JSON.parse(init.body);
            } catch {
              return null;
            }
          }

          function getPath(url) {
            const parsed = new URL(url, window.location.origin);
            return parsed.pathname.replace('/api', '');
          }

          function getSessionId(path, fallbackId) {
            const match = path.match(/\\/chat\\/sessions\\/(\\d+)/);
            if (match) {
              return Number.parseInt(match[1], 10);
            }

            return Number.isInteger(fallbackId) ? fallbackId : state.defaultSession?.id ?? 1;
          }

          function ensureSessionMessages(sessionId) {
            const key = String(sessionId);
            if (!Array.isArray(state.messagesBySession[key])) {
              state.messagesBySession[key] = [];
            }
            return state.messagesBySession[key];
          }

          function ensureSessionDraft(sessionId) {
            const key = String(sessionId);
            if (!state.draftsBySession[key]) {
              state.draftsBySession[key] = {
                content: '',
                model: state.models?.defaultModelRef || state.models?.defaultModel || '',
                thinking: { enabled: false, budget: 'standard' },
                attachedFileIds: [],
              };
            }
            return state.draftsBySession[key];
          }

          function appendMessage(sessionId, message) {
            const messages = ensureSessionMessages(sessionId);
            const nextMessage = {
              id: state.nextMessageId++,
              sessionId,
              role: message.role || 'assistant',
              content: typeof message.content === 'string' ? message.content : '',
              suggestion: message.suggestion ?? null,
              attachments: Array.isArray(message.attachments) ? message.attachments : [],
              createdAt: '2026-06-04T00:00:00Z',
            };
            messages.push(nextMessage);
            return nextMessage;
          }

          function ensureUserMessage(sessionId, body) {
            const userInput = typeof body?.userInput === 'string' ? body.userInput : '';
            const messages = ensureSessionMessages(sessionId);
            const existingLastMessage = messages[messages.length - 1];

            if (
              existingLastMessage?.role === 'user' &&
              existingLastMessage?.content === userInput
            ) {
              return existingLastMessage;
            }

            return appendMessage(sessionId, {
              role: 'user',
              content: userInput,
              attachments: [],
            });
          }

          function buildEventBlock(event) {
            const kind = typeof event?.kind === 'string' ? event.kind : '';
            let payload = {};

            if (kind === 'delta') {
              payload = { text: typeof event.text === 'string' ? event.text : '' };
            } else if (kind === 'tool_status') {
              payload = event.payload ?? {};
            } else if (kind === 'proposal') {
              payload = { proposal: event.proposal ?? null };
            } else if (kind === 'suggestion') {
              payload = { suggestion: event.suggestion ?? null };
            } else if (kind === 'done') {
              payload = { text: typeof event.text === 'string' ? event.text : '' };
            } else if (kind === 'error') {
              payload = {
                message: typeof event.message === 'string' ? event.message : 'stream error',
                code: typeof event.code === 'string' ? event.code : 'stream_error',
              };
            } else {
              return '';
            }

            return `event: ${kind}\\ndata: ${JSON.stringify(payload)}\\n\\n`;
          }

          window.fetch = async (input, init = {}) => {
            const requestUrl = typeof input === 'string' ? input : input?.url || '';

            if (!requestUrl.includes('/api/')) {
              return nativeFetch(input, init);
            }

            const path = getPath(requestUrl);
            const method = (init.method || 'GET').toUpperCase();
            const body = parseBody(init);
            const sessionId = getSessionId(path, body?.sessionId);

            if (method === 'GET' && path === '/profile') {
              return jsonResponse(state.profile);
            }

            if (method === 'PUT' && path === '/profile') {
              state.profile = body ?? state.profile;
              return jsonResponse(state.profile);
            }

            if (method === 'GET' && path === '/weekly-plan') {
              return jsonResponse(state.weeklyPlan);
            }

            if (method === 'PUT' && path === '/weekly-plan') {
              state.weeklyPlan = body ?? state.weeklyPlan;
              return jsonResponse(state.weeklyPlan);
            }

            if (method === 'GET' && path === '/daily-log') {
              return jsonResponse(state.dailyLog);
            }

            if (method === 'GET' && path === '/models') {
              return jsonResponse(state.models);
            }

            if (method === 'GET' && path === '/model-config') {
              return jsonResponse(state.modelConfig ?? { version: 1, providers: [] });
            }

            if (method === 'GET' && path === '/chat/sessions/default') {
              return jsonResponse(state.defaultSession);
            }

            if (method === 'GET' && path === '/chat/sessions') {
              return jsonResponse(state.sessions);
            }

            if (method === 'POST' && path === '/chat/sessions') {
              const nextSession = {
                id: state.sessions.length + 1,
                title: '新对话',
                createdAt: '2026-06-04T00:00:00Z',
                updatedAt: '2026-06-04T00:00:00Z',
              };
              state.sessions = [nextSession, ...state.sessions.filter((item) => item.id !== nextSession.id)];
              ensureSessionMessages(nextSession.id);
              ensureSessionDraft(nextSession.id);
              return jsonResponse(nextSession);
            }

            if (method === 'GET' && path.match(/^\\/chat\\/sessions\\/\\d+\\/messages$/)) {
              return jsonResponse(ensureSessionMessages(sessionId));
            }

            if (path.match(/^\\/chat\\/sessions\\/\\d+\\/draft$/)) {
              if (method === 'GET') {
                return jsonResponse(ensureSessionDraft(sessionId));
              }

              if (method === 'PUT') {
                state.draftsBySession[String(sessionId)] = {
                  ...ensureSessionDraft(sessionId),
                  ...(body ?? {}),
                };
                return jsonResponse({ ok: true });
              }
            }

            if (method === 'GET' && path.match(/^\\/chat\\/background\\//)) {
              const taskId = path.split('/').pop();
              return jsonResponse(state.backgroundTasks?.[taskId] ?? { task_id: taskId, status: 'not_found' });
            }

            if (method === 'POST' && path === '/chat/reply') {
              state.replyCalls.push(body);
              ensureUserMessage(sessionId, body);
              const replyScenario = state.replyScenarios.shift() ?? { text: '', suggestion: null, proposal: null };
              appendMessage(sessionId, {
                role: 'assistant',
                content: replyScenario.text || '',
                suggestion: replyScenario.proposal ?? replyScenario.suggestion ?? null,
              });
              return jsonResponse(replyScenario);
            }

            if (method === 'POST' && path === '/chat/stream') {
              state.streamCalls.push(body);
              ensureUserMessage(sessionId, body);
              const scenario = state.streamScenarios.shift();

              if (!scenario) {
                return jsonResponse({ message: 'missing stream scenario' }, 500);
              }

              if (scenario.type === 'http_error') {
                return jsonResponse(
                  { message: scenario.message || 'stream error' },
                  Number.isFinite(scenario.status) ? scenario.status : 503,
                );
              }

              const events = Array.isArray(scenario.events) ? scenario.events : [];
              const streamState = {
                fullText: '',
                proposal: null,
                suggestion: null,
                persisted: false,
              };

              const stream = new ReadableStream({
                start(controller) {
                  let cursor = 0;

                  function persistAssistant(finalText) {
                    if (streamState.persisted || !finalText) {
                      return;
                    }

                    appendMessage(sessionId, {
                      role: 'assistant',
                      content: finalText,
                      suggestion: streamState.proposal ?? streamState.suggestion ?? null,
                    });
                    streamState.persisted = true;
                  }

                  function emitNext() {
                    if (cursor >= events.length) {
                      controller.close();
                      return;
                    }

                    const event = events[cursor++];
                    const delayMs = Number.isFinite(event?.delayMs) ? event.delayMs : 0;

                    window.setTimeout(() => {
                      if (event?.kind === 'disconnect') {
                        controller.close();
                        return;
                      }

                      if (event?.kind === 'delta' && typeof event.text === 'string') {
                        streamState.fullText += event.text;
                      }

                      if (event?.kind === 'proposal') {
                        streamState.proposal = event.proposal ?? null;
                      }

                      if (event?.kind === 'suggestion') {
                        streamState.suggestion = event.suggestion ?? null;
                      }

                      const block = buildEventBlock(event);
                      if (block) {
                        controller.enqueue(encoder.encode(block));
                        state.eventLog.push({
                          kind: event.kind,
                          text: typeof event.text === 'string' ? event.text : '',
                        });
                      }

                      if (event?.kind === 'done') {
                        const finalText =
                          typeof event.text === 'string' && event.text
                            ? event.text
                            : streamState.fullText;
                        persistAssistant(finalText);
                        controller.close();
                        return;
                      }

                      if (event?.kind === 'error') {
                        controller.close();
                        return;
                      }

                      emitNext();
                    }, delayMs);
                  }

                  emitNext();
                },
              });

              return new Response(stream, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }

            if (method === 'POST' && path === '/tools/plan/commit') {
              state.commitCalls.push(body);
              const commitResult = state.commitResult ?? { ok: true, message: '已采纳', plan: state.weeklyPlan };
              if (commitResult?.plan) {
                state.weeklyPlan = jsonClone(commitResult.plan);
              }
              return jsonResponse(commitResult);
            }

            if (method === 'POST' && path === '/tools/plan/ignore') {
              state.ignoreCalls.push(body);
              return jsonResponse({ ok: true });
            }

            return jsonResponse({ ok: true });
          };
        })();
        """
        % json.dumps(config, ensure_ascii=False)
    )


def get_message_texts(page):
    return page.locator("article.group").evaluate_all(
        """(nodes) =>
          nodes.map((node) => (node.innerText || '').replace(/\\s+/g, ' ').trim()).filter(Boolean)
        """
    )
