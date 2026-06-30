# Retrieval Debug Log - Qwen3-4B-GGUF Q4_K_M / reranker on

## q1 검색 디버그

질문: 개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?

### LLM unit selection

```json
{
  "question_plan": {
    "enabled": true,
    "question": "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
    "answer_style": "list",
    "requires_comprehensive_coverage": true,
    "requirements": [
      {
        "id": "R1",
        "requirement": "개인통관고유부호 발급을 위해 필요한 앱 이름",
        "type": "fact"
      },
      {
        "id": "R2",
        "requirement": "앱 설치 후 메뉴 선택 방법",
        "type": "fact"
      },
      {
        "id": "R3",
        "requirement": "개인통관고유부호 발급 절차 요약",
        "type": "procedure"
      }
    ],
    "retrieval_queries": [
      "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
      "개인통관고유부호 발급 방법",
      "개인통관고유부호 발급 절차"
    ],
    "raw": {
      "answer_style": "list",
      "requires_comprehensive_coverage": true,
      "requirements": [
        {
          "id": "R1",
          "requirement": "개인통관고유부호 발급을 위해 필요한 앱 이름",
          "type": "fact"
        },
        {
          "id": "R2",
          "requirement": "앱 설치 후 메뉴 선택 방법",
          "type": "fact"
        },
        {
          "id": "R3",
          "requirement": "개인통관고유부호 발급 절차 요약",
          "type": "procedure"
        }
      ],
      "retrieval_queries": [
        "개인통관고유부호 발급 방법",
        "개인통관고유부호 발급 절차"
      ]
    }
  },
  "query_plan": {
    "enabled": true,
    "queries": [
      "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
      "개인통관고유부호 발급 방법",
      "개인통관고유부호 발급 절차"
    ],
    "source": "question_planner"
  },
  "retrieval_diagnostics": {
    "queries": [
      "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
      "개인통관고유부호 발급 방법",
      "개인통관고유부호 발급 절차"
    ],
    "per_query": [
      {
        "query_index": 1,
        "query": "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
        "context_count": 28
      },
      {
        "query_index": 2,
        "query": "개인통관고유부호 발급 방법",
        "context_count": 28
      },
      {
        "query_index": 3,
        "query": "개인통관고유부호 발급 절차",
        "context_count": 24
      }
    ]
  },
  "unit_selection_raw": {
    "selected_unit_ids": [],
    "additional_explanation": "grounded 모드에서는 최종 composer가 답변을 생성하므로 selector는 생략했습니다.",
    "selector_skipped": true
  },
  "raw_selected_units": [],
  "extractive_answer_before_generation": "② 설치된 ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택 ‘모바일관세청‘ 앱(App) 또는 개인통관고유부호 웹(Web) 사이트에 접속하여 발급 가능합니다",
  "render_diagnostics": {
    "render_mode": "grounded_seed",
    "seed_unit_ids": [
      "U3",
      "U2",
      "U1",
      "U5"
    ],
    "extractive_answer_before_generation": "② 설치된 ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택 ‘모바일관세청‘ 앱(App) 또는 개인통관고유부호 웹(Web) 사이트에 접속하여 발급 가능합니다",
    "grounded_generation": {
      "enabled": true,
      "reason": "ok",
      "used_evidence_ids": [
        "G1"
      ],
      "evidence_count": 3,
      "total_evidence_candidates": 20,
      "safe_token_budget": 3200,
      "attempts": [
        {
          "pass": 1,
          "strict_synthesis": false,
          "evidence_count": 3,
          "ok": true,
          "plain_fallback_used": false
        }
      ],
      "question_plan": {
        "enabled": true,
        "question": "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
        "answer_style": "list",
        "requires_comprehensive_coverage": true,
        "requirements": [
          {
            "id": "R1",
            "requirement": "개인통관고유부호 발급을 위해 필요한 앱 이름",
            "type": "fact"
          },
          {
            "id": "R2",
            "requirement": "앱 설치 후 메뉴 선택 방법",
            "type": "fact"
          },
          {
            "id": "R3",
            "requirement": "개인통관고유부호 발급 절차 요약",
            "type": "procedure"
          }
        ],
        "retrieval_queries": [
          "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
          "개인통관고유부호 발급 방법",
          "개인통관고유부호 발급 절차"
        ],
        "raw": {
          "answer_style": "list",
          "requires_comprehensive_coverage": true,
          "requirements": [
            {
              "id": "R1",
              "requirement": "개인통관고유부호 발급을 위해 필요한 앱 이름",
              "type": "fact"
            },
            {
              "id": "R2",
              "requirement": "앱 설치 후 메뉴 선택 방법",
              "type": "fact"
            },
            {
              "id": "R3",
              "requirement": "개인통관고유부호 발급 절차 요약",
              "type": "procedure"
            }
          ],
          "retrieval_queries": [
            "개인통관고유부호 발급 방법",
            "개인통관고유부호 발급 절차"
          ]
        }
      },
      "raw": {
        "final_answer": "개인통관고유부호를 발급하려면 ‘모바일 관세청’ 앱을 설치해야 하며, 앱 실행 후 [개인통관고유부호] 메뉴를 선택해야 합니다. 앱 설치 후 메뉴 선택 방법은 다음과 같습니다.\n\n1. ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택\n2. 성명, 주민등록번호, 휴대전화번호 기재 후 본인인증 진행\n3. 본인인증이 완료되면 [확인] 클릭 → 주소, 전화번호, 이메일(선택) 기재 및 동의여부 체크 후 [등록] 클릭 → 즉시 발급 완료\n\n또한, 웹사이트를 이용하는 방법도 있습니다. 포털사이트에서 [개인통관고유부호] 검색 → 개인통관고유부호 발급 웹 사이트 접속 → 신규발급 선택 → 본인인증 방법(휴대폰인증, 간편인증) 선택 및 성명, 주민등록번호, 자동입력방지코드 기재 및 실명인증 버튼 클릭 → 선택한 인증 방법에 따라 본인인증 진행 → [확인] 클릭 → 신청서 작성 후 [등록] 클릭 → 즉시 발급 완료.",
        "used_evidence_ids": [
          "G1"
        ],
        "covered_requirements": {
          "R1": true,
          "R2": true,
          "R3": true
        },
        "missing_requirements": [],
        "additional_explanation": "없음"
      }
    }
  },
  "coverage_diagnostics": {
    "before": {},
    "after": {},
    "reason": "deferred_to_grounded_composer"
  },
  "generated_coverage_diagnostics": {
    "ok": true,
    "intent": "availability",
    "missing_critical_terms": [],
    "required_min_items": 0,
    "rendered_item_count": 0,
    "repaired": false,
    "reason": "ok"
  },
  "generation_diagnostics": {
    "enabled": true,
    "reason": "ok",
    "used_evidence_ids": [
      "G1"
    ],
    "evidence_count": 3,
    "total_evidence_candidates": 20,
    "safe_token_budget": 3200,
    "attempts": [
      {
        "pass": 1,
        "strict_synthesis": false,
        "evidence_count": 3,
        "ok": true,
        "plain_fallback_used": false
      }
    ],
    "question_plan": {
      "enabled": true,
      "question": "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
      "answer_style": "list",
      "requires_comprehensive_coverage": true,
      "requirements": [
        {
          "id": "R1",
          "requirement": "개인통관고유부호 발급을 위해 필요한 앱 이름",
          "type": "fact"
        },
        {
          "id": "R2",
          "requirement": "앱 설치 후 메뉴 선택 방법",
          "type": "fact"
        },
        {
          "id": "R3",
          "requirement": "개인통관고유부호 발급 절차 요약",
          "type": "procedure"
        }
      ],
      "retrieval_queries": [
        "개인통관고유부호를 발급하려면 어떤 앱을 설치해야 하며, 설치 후 어떤 메뉴를 선택해야 하나요?",
        "개인통관고유부호 발급 방법",
        "개인통관고유부호 발급 절차"
      ],
      "raw": {
        "answer_style": "list",
        "requires_comprehensive_coverage": true,
        "requirements": [
          {
            "id": "R1",
            "requirement": "개인통관고유부호 발급을 위해 필요한 앱 이름",
            "type": "fact"
          },
          {
            "id": "R2",
            "requirement": "앱 설치 후 메뉴 선택 방법",
            "type": "fact"
          },
          {
            "id": "R3",
            "requirement": "개인통관고유부호 발급 절차 요약",
            "type": "procedure"
          }
        ],
        "retrieval_queries": [
          "개인통관고유부호 발급 방법",
          "개인통관고유부호 발급 절차"
        ]
      }
    },
    "raw": {
      "final_answer": "개인통관고유부호를 발급하려면 ‘모바일 관세청’ 앱을 설치해야 하며, 앱 실행 후 [개인통관고유부호] 메뉴를 선택해야 합니다. 앱 설치 후 메뉴 선택 방법은 다음과 같습니다.\n\n1. ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택\n2. 성명, 주민등록번호, 휴대전화번호 기재 후 본인인증 진행\n3. 본인인증이 완료되면 [확인] 클릭 → 주소, 전화번호, 이메일(선택) 기재 및 동의여부 체크 후 [등록] 클릭 → 즉시 발급 완료\n\n또한, 웹사이트를 이용하는 방법도 있습니다. 포털사이트에서 [개인통관고유부호] 검색 → 개인통관고유부호 발급 웹 사이트 접속 → 신규발급 선택 → 본인인증 방법(휴대폰인증, 간편인증) 선택 및 성명, 주민등록번호, 자동입력방지코드 기재 및 실명인증 버튼 클릭 → 선택한 인증 방법에 따라 본인인증 진행 → [확인] 클릭 → 신청서 작성 후 [등록] 클릭 → 즉시 발급 완료.",
      "used_evidence_ids": [
        "G1"
      ],
      "covered_requirements": {
        "R1": true,
        "R2": true,
        "R3": true
      },
      "missing_requirements": [],
      "additional_explanation": "없음"
    }
  },
  "top_candidate_units": [
    {
      "unit_id": "U1",
      "text": "∎ 공동인증서 인증은 PC 및 모바일관세청 앱(App)을 통하여 개인통관고유부호 발급이 가능하며, 금융인증서 인증은 현재 PC를 통한 발급만 가능합니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 7, p.13, 분할 0",
      "source_chunk_id": "section_7_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 11,
      "context_type": "retrieved",
      "score": 1.1723634661859081,
      "cross_score": 0.9248490929603577
    },
    {
      "unit_id": "U2",
      "text": "∎ ‘모바일관세청‘ 앱(App) 또는 개인통관고유부호 웹(Web) 사이트에 접속하여 발급 가능합니다",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.4-8",
      "locator": "섹션 3, p.4-8, 분할 0",
      "source_chunk_id": "section_3_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 3,
      "context_type": "retrieved",
      "score": 1.1504820165847385,
      "cross_score": 0.9583301544189453
    },
    {
      "unit_id": "U3",
      "text": "② 설치된 ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.4",
      "locator": "텍스트블록 8, 분할 0",
      "source_chunk_id": "p4_text_b8_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 1,
      "context_type": "retrieved",
      "score": 1.111841907365908,
      "cross_score": 0.9942243695259094
    },
    {
      "unit_id": "U4",
      "text": "② 설치된 ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택 모바일 관세청 앱 실행 개인통관고유부호 선택",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.4-8",
      "locator": "섹션 3, p.4-8, 분할 0",
      "source_chunk_id": "section_3_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 3,
      "context_type": "retrieved",
      "score": 1.1009060235236727,
      "cross_score": 0.9927541613578796
    },
    {
      "unit_id": "U5",
      "text": "∎ 모바일 관세청 앱(App) 이나 개인통관고유부호 사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속하여 신청할 수 있습니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.3",
      "locator": "섹션 1, p.3, 분할 0",
      "source_chunk_id": "section_1_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 14,
      "context_type": "retrieved",
      "score": 1.0842203216628183,
      "cross_score": 0.8966951370239258
    },
    {
      "unit_id": "U6",
      "text": "① [모바일관세청] 앱(App) 실행 후 [개인통관고유부호] 메뉴 선택",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16",
      "locator": "텍스트블록 4, 분할 0",
      "source_chunk_id": "p16_text_b4_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 2,
      "context_type": "retrieved",
      "score": 1.0515529686263967,
      "cross_score": 0.9935832619667053
    },
    {
      "unit_id": "U7",
      "text": "‣ 모바일 앱(App) 이용 시 [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회 (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드)",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 8, p.13, 분할 0",
      "source_chunk_id": "section_8_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 9,
      "context_type": "retrieved",
      "score": 1.0393743981146875,
      "cross_score": 0.9841926693916321
    },
    {
      "unit_id": "U8",
      "text": "① [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "섹션 9, p.14, 분할 0",
      "source_chunk_id": "section_9_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 10,
      "context_type": "retrieved",
      "score": 1.0379341042134669,
      "cross_score": 0.9904772043228149
    },
    {
      "unit_id": "U9",
      "text": "[모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "텍스트블록 13, 분할 0",
      "source_chunk_id": "p13_text_b13_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 8,
      "context_type": "retrieved",
      "score": 1.0326268351800514,
      "cross_score": 0.9757777452468872
    },
    {
      "unit_id": "U10",
      "text": "∎ 개인통관고유부호는 개인 식별을 위한 고유번호로 PC · 모바일에서 즉시 발급 가능하며, 한번 부여받은 부호는 계속 사용할 수 있습니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.3",
      "locator": "섹션 1, p.3, 분할 0",
      "source_chunk_id": "section_1_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 14,
      "context_type": "retrieved",
      "score": 0.9712558522299876,
      "cross_score": 0.721480667591095
    },
    {
      "unit_id": "U11",
      "text": "∎ PC에서 개인통관고유부호를 발급하는 방법은 다음과 같습니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.9-11",
      "locator": "섹션 4, p.9-11, 분할 0",
      "source_chunk_id": "section_4_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 1,
      "context_type": "retrieved",
      "score": 0.7391896014716015,
      "cross_score": 0.6225790977478027
    },
    {
      "unit_id": "U12",
      "text": "∎ 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 8, p.13, 분할 0",
      "source_chunk_id": "section_8_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 9,
      "context_type": "retrieved",
      "score": 0.631396384122378,
      "cross_score": 0.5739646553993225
    },
    {
      "unit_id": "U13",
      "text": "‣ 모바일 웹(Web) 이용 시 포털사이트에서 ‘개인통관고유부호’ 검색 후 개인통관고유부호 발급사이트 접속 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클 릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공인/금융인증서인 증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 8, p.13, 분할 0",
      "source_chunk_id": "section_8_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 9,
      "context_type": "retrieved",
      "score": 0.5277413455271783,
      "cross_score": 0.4748096168041229
    },
    {
      "unit_id": "U14",
      "text": "∎ 본인 명의 휴대폰이 없는 경우 개인통관고유부호 사이트에 접속하여 [공동/금융인증서]로 본인 인증하는 방법과 신분증 지참 후 가까운 세관에 방문하여 발급하는 방법이 있습니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 7, p.13, 분할 0",
      "source_chunk_id": "section_7_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 11,
      "context_type": "retrieved",
      "score": 0.47818731538711057,
      "cross_score": 0.28842294216156006
    },
    {
      "unit_id": "U15",
      "text": "④ ‘본인인증이 완료되었습니다. 개인통관고유부호 발급 신청하실 수 있습니다.’ 메시지에 [확인] 클릭 → 주소, 전화번호, 이메일(선택) 기재 및 동의여부 체크 후 [등록] 클릭 → 즉시 발급 완료 주소, 연락처 입력 및 열람 동의 후 등록",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.4-8",
      "locator": "섹션 3, p.4-8, 분할 0",
      "source_chunk_id": "section_3_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 3,
      "context_type": "retrieved",
      "score": 0.3674646901105486,
      "cross_score": 0.20456282794475555
    },
    {
      "unit_id": "U16",
      "text": "- 관세청 유니패스 사이트(https://unipass.customs.go.kr/csp/index.do) 메인화면 하단의 [개인통관고유 부호]를 클릭하거나, 각종 포털사이트에서 [개인통관고유부호]를 검색하여 사이트 접속 가능",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.3",
      "locator": "섹션 1, p.3, 분할 0",
      "source_chunk_id": "section_1_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 14,
      "context_type": "retrieved",
      "score": 0.36118194711962837,
      "cross_score": 0.17590676248073578
    },
    {
      "unit_id": "U17",
      "text": "∎ 개인통관고유부호를 사용정지 처리하는 경우 국내 통관에 사용이 불가하며, 동일 부호를 다 시 사용하고자 할 경우 정지→사용으로 변경 처리가 가능합니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "섹션 9, p.14, 분할 0",
      "source_chunk_id": "section_9_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 10,
      "context_type": "retrieved",
      "score": 0.320258581811538,
      "cross_score": 0.00880168192088604
    },
    {
      "unit_id": "U18",
      "text": "∎ 개인통관고유부호를 재발급하는 경우 기존 개인통관고유부호는 자동으로 ‘미사용’ 처리되 며, 신규 발급된 부호로만 통관이 가능합니다. (재발급 신청 연간 5회로 제한)",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "섹션 9, p.14, 분할 0",
      "source_chunk_id": "section_9_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 10,
      "context_type": "retrieved",
      "score": 0.298305577823868,
      "cross_score": 0.049098677933216095
    },
    {
      "unit_id": "U19",
      "text": "① 개인통관고유부호 사이트(https://unipass.customs.go.kr/csp/persIndex.do) 바로 접속하거나, 유니패스 사이트(https://unipass.customs.go.kr/csp/index.do) 하단 [개인통관고유부호] 클릭하여 진입",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.9-11",
      "locator": "섹션 4, p.9-11, 분할 0",
      "source_chunk_id": "section_4_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 1,
      "context_type": "retrieved",
      "score": 0.27650556938904375,
      "cross_score": 0.22214506566524506
    },
    {
      "unit_id": "U20",
      "text": "∎ 개인통관고유부호 발급 후 휴대전화번호가 변경된 경우 PC 및 모바일을 이용하여 휴대전화번호 변경이 가능하며 방법은 다음과 같습니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16-18",
      "locator": "섹션 12, p.16-18, 분할 0",
      "source_chunk_id": "section_12_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 15,
      "context_type": "parent_section",
      "score": 0.2586488446605498,
      "cross_score": 0.004151718690991402
    }
  ],
  "raw_context_count": 28,
  "candidate_unit_count": 83,
  "llm_unit_count": 24,
  "question_intent": "availability"
}
```

- E1 | rank=3 source=hybrid_rrf context_type=retrieved rrf=0.0217 dense=0.8961 bm25=3.0834 rerank=0.9925852417945862 | p.4-8 / section / 섹션 3, p.4-8, 분할 0 / section_3_0
  - 3. 모바일로 개인통관고유부호 신청하고 싶어요 ∎ ‘모바일관세청‘ 앱(App) 또는 개인통관고유부호 웹(Web) 사이트에 접속하여 발급 가능합니다 1. [모바일 관세청] 앱(App)에서 발급하는 방법은 다음과 같습니다. ① ‘모바일 관세청’ 앱 설치 ‣ 「플레이 스토어(Play Store)」 또는 「앱 스토어(App Store)」에서 ‘모바일 관세청’ 앱 검색하여 설치 Play 스토어 or App Store 진입 모바일 관세청 검색하여 설치 ② 설치된 ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택 모바일 관세청 앱 실행 개인통관고유부호 선택 ③ 성명, 주민등록번호, 휴대전화번호 기재 후 선택한 본인인증방법에 따라 본인인증 진행 [본인인증방법 ‘휴대전화’ 경우] ‣ 통신사 본인확인서비스(PASS) 창에서 이용 통신사 선택 후 상단 ‘간편본인확인(앱)’ 또는 ‘휴 대폰본인확인(문자)’ 선택하여 진행 ‣ 개인정보(이름, 생년월일, 휴대전화번호 등)는 자동 기입되며, 동의사항 체크 후 확인 ‣ 간편본인확인(앱) 인증 방식은 설치된 PASS 인증 앱(App)에서 본인인증을 진행하고, 휴대폰본인확인(문자)는 본인 휴대폰으로 전송된 인증번호 문자(SMS)를 확인 및 기재 PASS인증 앱을 이용하여 본인인증 진행 문자(SMS)로 본인인증 진행 [본인인증방법 ‘공동인증서’ 경우] ‣ 성명, 주민등록번호만 입력 후 본인인증 클릭 → 본인
- E2 | rank=10 source=hybrid_rrf context_type=retrieved rrf=0.0210 dense=0.8941 bm25=2.9841 rerank=0.9744291305541992 | p.14 / section / 섹션 9, p.14, 분할 0 / section_9_0
  - 9. 개인통관고유부호를 정지 또는 재발급 받고 싶어요 ∎ 개인통관고유부호를 사용정지 처리하는 경우 국내 통관에 사용이 불가하며, 동일 부호를 다 시 사용하고자 할 경우 정지→사용으로 변경 처리가 가능합니다. ∎ 개인통관고유부호를 재발급하는 경우 기존 개인통관고유부호는 자동으로 ‘미사용’ 처리되 며, 신규 발급된 부호로만 통관이 가능합니다. (재발급 신청 연간 5회로 제한) ※ 미사용 처리된 부호는 다시 사용 처리 불가 ‣ 모바일 앱(App) 이용 시 ① [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 ② 성명, 주민등록번호, 휴대전화번호 입력 후 본인인증방법에 따라 본인인증 후 조회 ③ 조회된 화면 하단 [수정] 버튼 클릭→사용여부 ‘사용정지’ 또는 '재발급'을 선택 후 [등록] 버튼 클릭 ‣ 모바일 웹(Web) 이용 시 ① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 버튼 클릭 ② 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 ③ 조회된 화면 하단 [수정] 버튼 클릭→사용여부 ‘사용정지’ 또는 '재발급'을 선택 후 [저장] 버튼 클릭 ① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭 ② 성명, 주민등록번호, 자동입력방지코드 입력하여 본
- E3 | rank=5 source=neighbor_expansion context_type=neighbor rrf=0.0258 dense=0.9220 bm25=0.8567 rerank=0.9904772043228149 | p.14 / text / 텍스트블록 5, 분할 0 / p14_text_b5_0
  - ※ 미사용 처리된 부호는 다시 사용 처리 불가
- E4 | rank=5 source=hybrid_rrf context_type=retrieved rrf=0.0258 dense=0.9220 bm25=0.8567 rerank=0.9904772043228149 | p.14 / text / 텍스트블록 7, 분할 0 / p14_text_b7_0
  - ① [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택
- E5 | rank=5 source=neighbor_expansion context_type=neighbor rrf=0.0258 dense=0.9220 bm25=0.8567 rerank=0.9904772043228149 | p.14 / text / 텍스트블록 8, 분할 0 / p14_text_b8_0
  - ② 성명, 주민등록번호, 휴대전화번호 입력 후 본인인증방법에 따라 본인인증 후 조회
- E6 | rank=5 source=neighbor_expansion context_type=neighbor rrf=0.0258 dense=0.9220 bm25=0.8567 rerank=0.9904772043228149 | p.14 / text / 텍스트블록 9, 분할 0 / p14_text_b9_0
  - ③ 조회된 화면 하단 [수정] 버튼 클릭→사용여부 ‘사용정지’ 또는 '재발급'을 선택 후 [등록] 버튼 클릭
- E7 | rank=2 source=neighbor_expansion context_type=neighbor rrf=0.0252 dense=0.9257 bm25=0.8358 rerank=0.9935832619667053 | p.16 / text / 텍스트블록 2, 분할 0 / p16_text_b2_0
  - 휴대전화번호 변경이 가능하며 방법은 다음과 같습니다.
- E8 | rank=2 source=hybrid_rrf context_type=retrieved rrf=0.0252 dense=0.9257 bm25=0.8358 rerank=0.9935832619667053 | p.16 / text / 텍스트블록 4, 분할 0 / p16_text_b4_0
  - ① [모바일관세청] 앱(App) 실행 후 [개인통관고유부호] 메뉴 선택
- E9 | rank=2 source=neighbor_expansion context_type=neighbor rrf=0.0252 dense=0.9257 bm25=0.8358 rerank=0.9935832619667053 | p.16 / text / 텍스트블록 5, 분할 0 / p16_text_b5_0
  - ② 본인인증방법(휴대전화, 간편인증), 성명, 주민등록번호, 변경된 휴대전화번호 기재 후 [본인인증] 클릭
- E10 | rank=2 source=neighbor_expansion context_type=neighbor rrf=0.0252 dense=0.9257 bm25=0.8358 rerank=0.9935832619667053 | p.16 / text / 텍스트블록 6, 분할 0 / p16_text_b6_0
  - ③ 다음 단계는 본인인증 방법에 따라 진행하세요
- E11 | rank=1 source=neighbor_expansion context_type=neighbor rrf=0.0235 dense=0.9168 bm25=0.8160 rerank=0.9942243695259094 | p.4 / text / 텍스트블록 6, 분할 0 / p4_text_b6_0
  - 모바일 관세청 검색하여 설치
- E12 | rank=1 source=hybrid_rrf context_type=retrieved rrf=0.0235 dense=0.9168 bm25=0.8160 rerank=0.9942243695259094 | p.4 / text / 텍스트블록 8, 분할 0 / p4_text_b8_0
  - ② 설치된 ‘모바일 관세청’ 앱 실행 후 [개인통관고유부호] 메뉴 선택
- E13 | rank=1 source=neighbor_expansion context_type=neighbor rrf=0.0235 dense=0.9168 bm25=0.8160 rerank=0.9942243695259094 | p.4 / text / 텍스트블록 9, 분할 0 / p4_text_b9_0
  - 모바일 관세청 앱 실행
- E14 | rank=1 source=neighbor_expansion context_type=neighbor rrf=0.0235 dense=0.9168 bm25=0.8160 rerank=0.9942243695259094 | p.4 / text / 텍스트블록 10, 분할 0 / p4_text_b10_0
  - 개인통관고유부호 선택
- E15 | rank=8 source=neighbor_expansion context_type=neighbor rrf=0.0226 dense=0.9165 bm25=0.7971 rerank=0.9757777452468872 | p.13 / text / 텍스트블록 12, 분할 0 / p13_text_b12_0
  - ‣ 모바일 앱(App) 이용 시
- E16 | rank=8 source=hybrid_rrf context_type=retrieved rrf=0.0226 dense=0.9165 bm25=0.7971 rerank=0.9757777452468872 | p.13 / text / 텍스트블록 13, 분할 0 / p13_text_b13_0
  - [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호
- E17 | rank=8 source=neighbor_expansion context_type=neighbor rrf=0.0226 dense=0.9165 bm25=0.7971 rerank=0.9757777452468872 | p.13 / text / 텍스트블록 14, 분할 0 / p13_text_b14_0
  - 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회
- E18 | rank=8 source=neighbor_expansion context_type=neighbor rrf=0.0226 dense=0.9165 bm25=0.7971 rerank=0.9757777452468872 | p.13 / text / 텍스트블록 15, 분할 0 / p13_text_b15_0
  - (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드)
- E19 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0156 dense=0.9175 bm25=0.0000 rerank=0.9917962551116943 | p.14 / text / 텍스트블록 20, 분할 0 / p14_text_b20_0
  - 10. 개인통관고유부호 항목 수정 방법을 알려주세요
- E20 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0156 dense=0.9175 bm25=0.0000 rerank=0.9917962551116943 | p.14 / text / 텍스트블록 21, 분할 0 / p14_text_b21_0
  - ∎ 개인통관고유부호 항목(주소, 전화번호 등) 수정 방법은 다음과 같습니다.
- E21 | rank=4 source=hybrid_rrf context_type=retrieved rrf=0.0156 dense=0.9175 bm25=0.0000 rerank=0.9917962551116943 | p.14 / text / 텍스트블록 22, 분할 0 / p14_text_b22_0
  - ‣ 모바일 앱(App) 이용 시 ① [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택
- E22 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0156 dense=0.9175 bm25=0.0000 rerank=0.9917962551116943 | p.14 / text / 텍스트블록 24, 분할 0 / p14_text_b24_0
  - ③ 조회된 화면 하단 [수정] 버튼 클릭 → 항목 수정 후 [등록] 버튼 클릭
- E23 | rank=6 source=hybrid_rrf context_type=retrieved rrf=0.0123 dense=0.0000 bm25=3.5758 rerank=0.9858953356742859 | p.4 / ocr / 페이지 이미지 OCR 0 / p4_ocr_0
  - [이미지/OCR 추출] Q 3. GH Ae 개인통관고유부호 신청하고 싶어요 ㅁ '모바일관세청' WApp) 또는 개인통관고유부호 BWeb) 사이트에 접속하여 발급 가능합니다 A 1. [모바일 관세청] MW Appa 발급하는 SAS 다음과 같습니다. © '모바일 관세청' eH 설치 ㆍ '「플레이 스토어(013/ Store); 또는 TOY 스토어(400 Store) OIA '모바일 관세청 OH 검색하여 설치 : Play 스토어 or App Store 진입 모바일 관세청 검색하여 설치 | =, a - Sr es cr or 안드로이드 폰 - 플레이스토어(013/ Store) > 22 100안이상 0 ㆍ ㅣ ~ | . ro . —s == @ ㅅㅅ ae 고 == - Ore =tipen eon Unirasc tela) sisal + 외는 Ste wea | @ 설치된 '모바일 관세청' HY 실행 후 [개인통관고유부호] 메뉴 선택 모바일 관세청 gy 실행 개인통관고유부호 선택 | | 모바일 관세청 ㅠㅠ. ㅣ > tmzes | Q | 드[크므 & Jeemzomaun [06220 | ssoman “ame 개 | oo 편 32 죄 | \ loess 수입화움진챙정보. 신고서차리헌화 혜외직구환급 : y : 개 eee | 06) ‘eo ) r 관련사이트 바로가기 ^ -4-
- E24 | rank=15 source=parent_section_expansion context_type=parent_section rrf=0.0320 dense=0.9271 bm25=7.1872 rerank=0.9930992126464844 | p.16-18 / section / 섹션 12, p.16-18, 분할 0 / section_12_0
  - 12. 부호 발급 후 휴대전화번호가 변경 되었어요 ∎ 개인통관고유부호 발급 후 휴대전화번호가 변경된 경우 PC 및 모바일을 이용하여 휴대전화번호 변경이 가능하며 방법은 다음과 같습니다. ‣ 모바일 앱(App) 이용 시 ① [모바일관세청] 앱(App) 실행 후 [개인통관고유부호] 메뉴 선택 ② 본인인증방법(휴대전화, 간편인증), 성명, 주민등록번호, 변경된 휴대전화번호 기재 후 [본인인증] 클릭 ③ 다음 단계는 본인인증 방법에 따라 진행하세요 * 휴대전화 : 본인인증 클릭 시 "휴대전화번호가 기존 번호와 일치하지 않습니다“ 메시지 확인 후 [확인] 클릭 → 통신사 본인확인서비스 사이트 이동 → 본인인증 완료 시 휴대전화번호 변경 완료 * 간편인증 : 간편인증 팝업창에서 서비스(카카오톡, 네이버 등) 선택 후 [다음] 클릭 → [모두 동의하고 인증요청] 클릭 → 개별서비스 앱에서 인증 진행 및 완료 시 휴대전화번호 변경 완료 ※ 공동인증서 인증을 통한 휴대전화번호 변경은 PC 에서만 가능합니다. ‣ 모바일 웹(Web) 이용 시 ① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 클릭 ② 성명과 주민등록번호, 자동입력방지코드, 본인인증 방법(휴대폰인증, 간편인증) 선택 후 [실명인증] ③ 다음 단계는 본인인증 방법에 따라 진행하세요 * 휴대폰인증 : 변경된 휴대전화번호 기재 후 [전송] 클릭 → 통신사 
- E25 | rank=9 source=hybrid_rrf context_type=retrieved rrf=0.0226 dense=0.9178 bm25=1.6636 rerank=0.9951978325843811 | p.13 / section / 섹션 8, p.13, 분할 0 / section_8_0
  - 8. 발급 받은 개인통관고유부호가 기억나지 않아요 ∎ 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수 ‣ 모바일 앱(App) 이용 시 [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회 (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드) ‣ 모바일 웹(Web) 이용 시 포털사이트에서 ‘개인통관고유부호’ 검색 후 개인통관고유부호 발급사이트 접속 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클 릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공인/금융인증서인 증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회
- E26 | rank=14 source=hybrid_rrf context_type=retrieved rrf=0.0210 dense=0.9148 bm25=1.5734 rerank=0.9934027791023254 | p.3 / section / 섹션 1, p.3, 분할 0 / section_1_0
  - 1. 개인통관고유부호는 무엇인가요? ∎ 관세청은 개인정보 유출을 방지하기 위하여 개인물품 수입신고 시 주민등록번호 대신 활용할 수 있는 개인통관고유부호 제도를 운영하고 있습니다. ∎ 개인통관고유부호는 개인 식별을 위한 고유번호로 PC · 모바일에서 즉시 발급 가능하며, 한번 부여받은 부호는 계속 사용할 수 있습니다. ∎ 모바일 관세청 앱(App) 이나 개인통관고유부호 사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속하여 신청할 수 있습니다. - 관세청 유니패스 사이트(https://unipass.customs.go.kr/csp/index.do) 메인화면 하단의 [개인통관고유 부호]를 클릭하거나, 각종 포털사이트에서 [개인통관고유부호]를 검색하여 사이트 접속 가능 ∎ 개인통관고유부호는 P로 시작하는 13자리 번호이며, PC · 모바일에서 실명인증 및 본인인증 후 조회
- E27 | rank=1 source=hybrid_rrf context_type=retrieved rrf=0.0184 dense=0.9070 bm25=1.5533 rerank=0.9992757439613342 | p.9-11 / section / 섹션 4, p.9-11, 분할 0 / section_4_0
  - 4. PC로 개인통관고유부호 신청하고 싶어요 ∎ PC에서 개인통관고유부호를 발급하는 방법은 다음과 같습니다. ① 개인통관고유부호 사이트(https://unipass.customs.go.kr/csp/persIndex.do) 바로 접속하거나, 유니패스 사이트(https://unipass.customs.go.kr/csp/index.do) 하단 [개인통관고유부호] 클릭하여 진입 ② [신규발급] 클릭 → ‘휴대폰인증’, ‘공동/금융인증서 인증’, ‘간편인증’ 중 한 가지 본인인증 방법 선택 → 성명, 주민등록번호, 자동입력방지코드 기재 후 [실명인증] 클릭 ※ 실명인증에 실패하는 경우 성명, 주민등록번호를 정확하게 기재했는지 확인 바라며, 지속적으로 오류가 발생한 다면 KCB 고객센터(☎02-708-1000)로 개인 실명정보 등록 및 명의도용 차단해제 여부를 확인해 주세요. ※ 본인 명의 휴대전화 또는 인증서가 없는 경우, 신분증 지참하여 가까운 세관 방문 후 발급 가능합니다. ③ 선택한 본인인증 방법으로 본인인증 진행 [휴대폰인증으로 본인인증 진행] ‣ 통신사 본인확인서비스(PASS) 창에서 본인 명의 이용 통신사 및 동의사항 체크 후 [문자(SMS)로 인증 하기] 클릭 → 이름, 생년월일/성별, 휴대폰번호, 보안문자 입력 후 [확인] → 문자로 수신된 인 증번호를 기재 후 [확인] ‣ [PASS로 인증하기] 클릭 시 설치된 PASS 인증 
- E28 | rank=11 source=hybrid_rrf context_type=retrieved rrf=0.0108 dense=0.9100 bm25=0.0000 rerank=0.9948339462280273 | p.13 / section / 섹션 7, p.13, 분할 0 / section_7_0
  - 7. 본인 명의가 아니라 휴대폰 인증이 안돼요 ∎ 본인 명의 휴대폰이 없는 경우 개인통관고유부호 사이트에 접속하여 [공동/금융인증서]로 본인 인증하는 방법과 신분증 지참 후 가까운 세관에 방문하여 발급하는 방법이 있습니다. ∎ 공동인증서 인증은 PC 및 모바일관세청 앱(App)을 통하여 개인통관고유부호 발급이 가능하며, 금융인증서 인증은 현재 PC를 통한 발급만 가능합니다.

## q2 검색 디버그

질문: 발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.

### LLM unit selection

```json
{
  "question_plan": {
    "enabled": true,
    "question": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
    "answer_style": "list",
    "requires_comprehensive_coverage": true,
    "requirements": [
      {
        "id": "R1",
        "requirement": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
        "type": "fact"
      }
    ],
    "retrieval_queries": [
      "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
      "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
      "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
    ],
    "raw": {
      "answer_style": "list",
      "requires_comprehensive_coverage": true,
      "requirements": [
        {
          "id": "R1",
          "requirement": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
          "type": "fact"
        }
      ],
      "retrieval_queries": [
        "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
        "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
      ]
    }
  },
  "query_plan": {
    "enabled": true,
    "queries": [
      "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
      "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
      "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
    ],
    "source": "question_planner"
  },
  "retrieval_diagnostics": {
    "queries": [
      "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
      "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
      "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
    ],
    "per_query": [
      {
        "query_index": 1,
        "query": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
        "context_count": 28
      },
      {
        "query_index": 2,
        "query": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
        "context_count": 28
      },
      {
        "query_index": 3,
        "query": "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법",
        "context_count": 28
      }
    ]
  },
  "unit_selection_raw": {
    "selected_unit_ids": [],
    "additional_explanation": "grounded 모드에서는 최종 composer가 답변을 생성하므로 selector는 생략했습니다.",
    "selector_skipped": true
  },
  "raw_selected_units": [],
  "extractive_answer_before_generation": "모바일 앱(App) 이용 시 [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회 (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드) 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수",
  "render_diagnostics": {
    "render_mode": "grounded_seed",
    "seed_unit_ids": [
      "U3",
      "U4",
      "U2",
      "U5",
      "U6"
    ],
    "extractive_answer_before_generation": "모바일 앱(App) 이용 시 [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회 (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드) 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수",
    "grounded_generation": {
      "enabled": true,
      "reason": "ok",
      "used_evidence_ids": [
        "G1"
      ],
      "evidence_count": 9,
      "total_evidence_candidates": 20,
      "safe_token_budget": 3200,
      "attempts": [
        {
          "pass": 1,
          "strict_synthesis": false,
          "evidence_count": 9,
          "ok": true,
          "plain_fallback_used": false
        }
      ],
      "question_plan": {
        "enabled": true,
        "question": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
        "answer_style": "list",
        "requires_comprehensive_coverage": true,
        "requirements": [
          {
            "id": "R1",
            "requirement": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
            "type": "fact"
          }
        ],
        "retrieval_queries": [
          "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
          "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
          "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
        ],
        "raw": {
          "answer_style": "list",
          "requires_comprehensive_coverage": true,
          "requirements": [
            {
              "id": "R1",
              "requirement": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
              "type": "fact"
            }
          ],
          "retrieval_queries": [
            "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
            "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
          ]
        }
      },
      "raw": {
        "final_answer": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로는 다음과 같습니다.\n\n1. 모바일 앱 이용: [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회\n\n2. 모바일 웹 이용: 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 본인인증 후 조회\n\n3. PC 이용: 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 본인인증 후 조회",
        "used_evidence_ids": [
          "G1"
        ],
        "covered_requirements": {
          "R1": true
        },
        "missing_requirements": [],
        "additional_explanation": "없음"
      }
    }
  },
  "coverage_diagnostics": {
    "before": {},
    "after": {},
    "reason": "deferred_to_grounded_composer"
  },
  "generated_coverage_diagnostics": {
    "ok": true,
    "intent": "list",
    "missing_critical_terms": [],
    "required_min_items": 2,
    "rendered_item_count": 8,
    "repaired": false,
    "reason": "ok"
  },
  "generation_diagnostics": {
    "enabled": true,
    "reason": "ok",
    "used_evidence_ids": [
      "G1"
    ],
    "evidence_count": 9,
    "total_evidence_candidates": 20,
    "safe_token_budget": 3200,
    "attempts": [
      {
        "pass": 1,
        "strict_synthesis": false,
        "evidence_count": 9,
        "ok": true,
        "plain_fallback_used": false
      }
    ],
    "question_plan": {
      "enabled": true,
      "question": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
      "answer_style": "list",
      "requires_comprehensive_coverage": true,
      "requirements": [
        {
          "id": "R1",
          "requirement": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
          "type": "fact"
        }
      ],
      "retrieval_queries": [
        "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로를 모두 나열하세요.",
        "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
        "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
      ],
      "raw": {
        "answer_style": "list",
        "requires_comprehensive_coverage": true,
        "requirements": [
          {
            "id": "R1",
            "requirement": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
            "type": "fact"
          }
        ],
        "retrieval_queries": [
          "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로",
          "개인통관고유부호를 잊어버렸을 때 대체적으로 사용할 수 있는 방법"
        ]
      }
    },
    "raw": {
      "final_answer": "발급받은 개인통관고유부호가 기억나지 않을 때 조회 가능한 이용 경로는 다음과 같습니다.\n\n1. 모바일 앱 이용: [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회\n\n2. 모바일 웹 이용: 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 본인인증 후 조회\n\n3. PC 이용: 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 본인인증 후 조회",
      "used_evidence_ids": [
        "G1"
      ],
      "covered_requirements": {
        "R1": true
      },
      "missing_requirements": [],
      "additional_explanation": "없음"
    }
  },
  "top_candidate_units": [
    {
      "unit_id": "U1",
      "text": "‣ 모바일 웹(Web) 이용 시 포털사이트에서 ‘개인통관고유부호’ 검색 후 개인통관고유부호 발급사이트 접속 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클 릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공인/금융인증서인 증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 8, p.13, 분할 0",
      "source_chunk_id": "section_8_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 1,
      "context_type": "retrieved",
      "score": 1.3261079522177726,
      "cross_score": 0.7175959348678589
    },
    {
      "unit_id": "U2",
      "text": "① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "섹션 10, p.14, 분할 0",
      "source_chunk_id": "section_10_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 4,
      "context_type": "parent_section",
      "score": 0.8302105094279725,
      "cross_score": 0.8039872646331787
    },
    {
      "unit_id": "U3",
      "text": "‣ 모바일 앱(App) 이용 시 [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회 (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드)",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "섹션 8, p.13, 분할 0",
      "source_chunk_id": "section_8_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 1,
      "context_type": "retrieved",
      "score": 0.7459649735495598,
      "cross_score": 0.247702956199646
    },
    {
      "unit_id": "U4",
      "text": "∎ 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "텍스트블록 10, 분할 0",
      "source_chunk_id": "p13_text_b10_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 1,
      "context_type": "neighbor",
      "score": 0.6707875826496041,
      "cross_score": 0.478671133518219
    },
    {
      "unit_id": "U5",
      "text": "② 개명 후 성명과 주민등록번호 입력하여 선택한 본인인증 방법(휴대전화, 공동인증서, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.15",
      "locator": "섹션 11, p.15, 분할 0",
      "source_chunk_id": "section_11_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 7,
      "context_type": "parent_section",
      "score": 0.6260669687414713,
      "cross_score": 0.4399915933609009
    },
    {
      "unit_id": "U6",
      "text": "② 개명 후 성명과 주민등록번호, 자동입력방지코드 입력하여 선택한 본인인증 방법(휴대폰인증, 공동/금 융인증서인증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.15",
      "locator": "섹션 11, p.15, 분할 0",
      "source_chunk_id": "section_11_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 7,
      "context_type": "parent_section",
      "score": 0.6039327951098031,
      "cross_score": 0.3811074197292328
    },
    {
      "unit_id": "U7",
      "text": "① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 클릭",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16-18",
      "locator": "섹션 12, p.16-18, 분할 0",
      "source_chunk_id": "section_12_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 5,
      "context_type": "retrieved",
      "score": 0.5765012967542971,
      "cross_score": 0.5651925206184387
    },
    {
      "unit_id": "U8",
      "text": "② 개명 후 성명과 주민등록번호, 자동입력방지코드 입력하여 선택한 본인인증 방법(휴대폰인증, 간편인 증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.15",
      "locator": "섹션 11, p.15, 분할 0",
      "source_chunk_id": "section_11_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 7,
      "context_type": "parent_section",
      "score": 0.5137347472334451,
      "cross_score": 0.33665937185287476
    },
    {
      "unit_id": "U9",
      "text": "① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 버튼 클릭",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "섹션 10, p.14, 분할 0",
      "source_chunk_id": "section_10_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 4,
      "context_type": "parent_section",
      "score": 0.46566137469667973,
      "cross_score": 0.400438129901886
    },
    {
      "unit_id": "U10",
      "text": "개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.13",
      "locator": "텍스트블록 21, 분할 0",
      "source_chunk_id": "p13_text_b21_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 10,
      "context_type": "retrieved",
      "score": 0.42410721638243953,
      "cross_score": 0.3388165235519409
    },
    {
      "unit_id": "U11",
      "text": "융인증서인증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.15",
      "locator": "텍스트블록 15, 분할 0",
      "source_chunk_id": "p15_text_b15_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 7,
      "context_type": "neighbor",
      "score": 0.4199202787304468,
      "cross_score": 0.2398449033498764
    },
    {
      "unit_id": "U12",
      "text": "증)에 따라 실명인증및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "텍스트블록 18, 분할 0",
      "source_chunk_id": "p14_text_b18_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 5,
      "context_type": "neighbor",
      "score": 0.3678891441188659,
      "cross_score": 0.23892034590244293
    },
    {
      "unit_id": "U13",
      "text": "① 개인통관고유부호 발급 시스템 이용 ② 관세청 홈페이지 [해외직구 여기로!] 이용",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.17",
      "locator": "텍스트블록 2, 분할 0",
      "source_chunk_id": "p17_text_b2_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 9,
      "context_type": "neighbor",
      "score": 0.3671472509233886,
      "cross_score": 0.2661890685558319
    },
    {
      "unit_id": "U14",
      "text": "증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.15",
      "locator": "텍스트블록 12, 분할 0",
      "source_chunk_id": "p15_text_b12_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 7,
      "context_type": "neighbor",
      "score": 0.36181781465058993,
      "cross_score": 0.23424243927001953
    },
    {
      "unit_id": "U15",
      "text": "∎ 개인통관고유부호로 통관된 해외직구 이력은 2가지 방법으로 조회 가능합니다.",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.17",
      "locator": "텍스트블록 1, 분할 0",
      "source_chunk_id": "p17_text_b1_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 9,
      "context_type": "neighbor",
      "score": 0.34764406517433466,
      "cross_score": 0.19418588280677795
    },
    {
      "unit_id": "U16",
      "text": "② 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공동/금융인증서인증, 간편인",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.14",
      "locator": "텍스트블록 17, 분할 0",
      "source_chunk_id": "p14_text_b17_0",
      "source_kind": "text",
      "source_role": "body",
      "context_rank": 5,
      "context_type": "neighbor",
      "score": 0.30298083898781175,
      "cross_score": 0.0006787074380554259
    },
    {
      "unit_id": "U17",
      "text": "② 본인인증방법(휴대전화, 간편인증), 성명, 주민등록번호, 변경된 휴대전화번호 기재 후 [본인인증] 클릭",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16-18",
      "locator": "섹션 12, p.16-18, 분할 0",
      "source_chunk_id": "section_12_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 5,
      "context_type": "retrieved",
      "score": 0.300190142903158,
      "cross_score": 0.0007980334339663386
    },
    {
      "unit_id": "U18",
      "text": "① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 클릭",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16-18",
      "locator": "섹션 12, p.16-18, 분할 0",
      "source_chunk_id": "section_12_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 5,
      "context_type": "retrieved",
      "score": 0.29977196096938497,
      "cross_score": 0.2472131848335266
    },
    {
      "unit_id": "U19",
      "text": "* 간편인증 : 간편인증 팝업창에서 서비스(카카오톡, 네이버 등) 선택, 변경된 휴대전화번호 입력하여 [다음] 클릭 → [모두 동의하고 인증요청] 클릭 → 개별서비스 앱에서 인증 진행 및 완료 시 개인통관고유부호 상의 휴대전화번호 변경 완료",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16-18",
      "locator": "섹션 12, p.16-18, 분할 0",
      "source_chunk_id": "section_12_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 5,
      "context_type": "retrieved",
      "score": 0.2790949104757274,
      "cross_score": 0.008286134339869022
    },
    {
      "unit_id": "U20",
      "text": "* 간편인증 : 간편인증 팝업창에서 서비스(카카오톡, 네이버 등) 선택 후 [다음] 클릭 → [모두 동의하고 인증요청] 클릭 → 개별서비스 앱에서 인증 진행 및 완료 시 휴대전화번호 변경 완료",
      "title": "개인통관고유부호 발급 시스템이용 FAQ.pdf",
      "page": "p.16-18",
      "locator": "섹션 12, p.16-18, 분할 0",
      "source_chunk_id": "section_12_0",
      "source_kind": "section",
      "source_role": "section",
      "context_rank": 5,
      "context_type": "retrieved",
      "score": 0.23196820771945564,
      "cross_score": 0.0001594315835973248
    }
  ],
  "raw_context_count": 28,
  "candidate_unit_count": 49,
  "llm_unit_count": 24,
  "question_intent": "list"
}
```

- E1 | rank=5 source=hybrid_rrf context_type=retrieved rrf=0.0137 dense=0.0000 bm25=3.7846 rerank=0.8519972562789917 | p.16-18 / section / 섹션 12, p.16-18, 분할 0 / section_12_0
  - 12. 부호 발급 후 휴대전화번호가 변경 되었어요 ∎ 개인통관고유부호 발급 후 휴대전화번호가 변경된 경우 PC 및 모바일을 이용하여 휴대전화번호 변경이 가능하며 방법은 다음과 같습니다. ‣ 모바일 앱(App) 이용 시 ① [모바일관세청] 앱(App) 실행 후 [개인통관고유부호] 메뉴 선택 ② 본인인증방법(휴대전화, 간편인증), 성명, 주민등록번호, 변경된 휴대전화번호 기재 후 [본인인증] 클릭 ③ 다음 단계는 본인인증 방법에 따라 진행하세요 * 휴대전화 : 본인인증 클릭 시 "휴대전화번호가 기존 번호와 일치하지 않습니다“ 메시지 확인 후 [확인] 클릭 → 통신사 본인확인서비스 사이트 이동 → 본인인증 완료 시 휴대전화번호 변경 완료 * 간편인증 : 간편인증 팝업창에서 서비스(카카오톡, 네이버 등) 선택 후 [다음] 클릭 → [모두 동의하고 인증요청] 클릭 → 개별서비스 앱에서 인증 진행 및 완료 시 휴대전화번호 변경 완료 ※ 공동인증서 인증을 통한 휴대전화번호 변경은 PC 에서만 가능합니다. ‣ 모바일 웹(Web) 이용 시 ① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 클릭 ② 성명과 주민등록번호, 자동입력방지코드, 본인인증 방법(휴대폰인증, 간편인증) 선택 후 [실명인증] ③ 다음 단계는 본인인증 방법에 따라 진행하세요 * 휴대폰인증 : 변경된 휴대전화번호 기재 후 [전송] 클릭 → 통신사 
- E2 | rank=1 source=neighbor_expansion context_type=neighbor rrf=0.0250 dense=0.9060 bm25=12.3204 rerank=0.9940534234046936 | p.13 / text / 텍스트블록 7, 분할 0 / p13_text_b7_0
  - ∎ 공동인증서 인증은 PC 및 모바일관세청 앱(App)을 통하여 개인통관고유부호 발급이 가능하며,
- E3 | rank=1 source=neighbor_expansion context_type=neighbor rrf=0.0250 dense=0.9060 bm25=12.3204 rerank=0.9940534234046936 | p.13 / text / 텍스트블록 8, 분할 0 / p13_text_b8_0
  - 금융인증서 인증은 현재 PC를 통한 발급만 가능합니다.
- E4 | rank=1 source=hybrid_rrf context_type=retrieved rrf=0.0250 dense=0.9060 bm25=12.3204 rerank=0.9940534234046936 | p.13 / text / 텍스트블록 9, 분할 0 / p13_text_b9_0
  - 8. 발급 받은 개인통관고유부호가 기억나지 않아요
- E5 | rank=1 source=neighbor_expansion context_type=neighbor rrf=0.0250 dense=0.9060 bm25=12.3204 rerank=0.9940534234046936 | p.13 / text / 텍스트블록 10, 분할 0 / p13_text_b10_0
  - ∎ 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수
- E6 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0286 dense=0.9136 bm25=12.0138 rerank=0.8823662400245667 | p.2 / text / 텍스트블록 5, 분할 0 / p2_text_b5_0
  - Q6. 부호 발급 시 주소는 어떤 주소를 기재하나요? ·············· 13
- E7 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0286 dense=0.9136 bm25=12.0138 rerank=0.8823662400245667 | p.2 / text / 텍스트블록 6, 분할 0 / p2_text_b6_0
  - Q7. 본인 명의가 아니라 휴대폰 인증이 안돼요····················· 13
- E8 | rank=4 source=hybrid_rrf context_type=retrieved rrf=0.0286 dense=0.9136 bm25=12.0138 rerank=0.8823662400245667 | p.2 / text / 텍스트블록 7, 분할 0 / p2_text_b7_0
  - Q8. 발급 받은 개인통관고유부호가 기억나지 않아요··········· 13
- E9 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0286 dense=0.9136 bm25=12.0138 rerank=0.8823662400245667 | p.2 / text / 텍스트블록 8, 분할 0 / p2_text_b8_0
  - Q9. 개인통관고유부호를 정지 또는 재발급 받고 싶어요······· 14
- E10 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0286 dense=0.9136 bm25=12.0138 rerank=0.8823662400245667 | p.2 / text / 텍스트블록 9, 분할 0 / p2_text_b9_0
  - Q10. 개인통관고유부호 항목 수정 방법을 알려주세요··········· 14
- E11 | rank=9 source=neighbor_expansion context_type=neighbor rrf=0.0209 dense=0.9068 bm25=2.9395 rerank=0.7363173961639404 | p.17 / text / 텍스트블록 1, 분할 0 / p17_text_b1_0
  - ∎ 개인통관고유부호로 통관된 해외직구 이력은 2가지 방법으로 조회 가능합니다.
- E12 | rank=9 source=neighbor_expansion context_type=neighbor rrf=0.0209 dense=0.9068 bm25=2.9395 rerank=0.7363173961639404 | p.17 / text / 텍스트블록 2, 분할 0 / p17_text_b2_0
  - ① 개인통관고유부호 발급 시스템 이용 ② 관세청 홈페이지 [해외직구 여기로!] 이용
- E13 | rank=9 source=hybrid_rrf context_type=retrieved rrf=0.0209 dense=0.9068 bm25=2.9395 rerank=0.7363173961639404 | p.17 / text / 텍스트블록 3, 분할 0 / p17_text_b3_0
  - 1. 개인통관고유부호 발급 시스템 이용 방법
- E14 | rank=9 source=neighbor_expansion context_type=neighbor rrf=0.0209 dense=0.9068 bm25=2.9395 rerank=0.7363173961639404 | p.17 / text / 텍스트블록 5, 분할 0 / p17_text_b5_0
  - ※ ‘사용’ 상태의 개인통관고유부호 통관 이력만 조회 가능
- E15 | rank=1 source=hybrid_rrf context_type=retrieved rrf=0.0323 dense=0.9204 bm25=6.3788 rerank=0.9972910284996033 | p.13 / section / 섹션 8, p.13, 분할 0 / section_8_0
  - 8. 발급 받은 개인통관고유부호가 기억나지 않아요 ∎ 개인통관고유부호는 PC 및 모바일 앱(App) 또는 웹(Web)사이트를 통해 언제든지 조회할 수 ‣ 모바일 앱(App) 이용 시 [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 → 성명, 주민등록번호, 휴대전화번호 를 입력 후 본인인증방법(휴대전화, 공동인증서, 간편인증)에 따라 본인인증 후 조회 (※ [모바일관세청] 앱(App)은 [App store 또는 Play 스토어]에서 다운로드) ‣ 모바일 웹(Web) 이용 시 포털사이트에서 ‘개인통관고유부호’ 검색 후 개인통관고유부호 발급사이트 접속 → [조회] 버튼 클릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클 릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공인/금융인증서인 증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회
- E16 | rank=4 source=parent_section_expansion context_type=parent_section rrf=0.0303 dense=0.9152 bm25=3.8671 rerank=0.9245610237121582 | p.14 / section / 섹션 10, p.14, 분할 0 / section_10_0
  - 10. 개인통관고유부호 항목 수정 방법을 알려주세요 ∎ 개인통관고유부호 항목(주소, 전화번호 등) 수정 방법은 다음과 같습니다. ‣ 모바일 앱(App) 이용 시 ① [모바일관세청] 앱 실행 후 [개인통관고유부호] 메뉴 선택 ② 성명, 주민등록번호, 휴대전화번호 입력 후 본인인증방법에 따라 본인인증 후 조회 ③ 조회된 화면 하단 [수정] 버튼 클릭 → 항목 수정 후 [등록] 버튼 클릭 ‣ 모바일 웹(Web) 이용 시 ① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 버튼 클릭 ② 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 ③ 조회된 화면 하단 [수정] 버튼 클릭 → 항목 수정 후 [저장] 버튼 클릭 ‣ PC 이용 ① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭 ② 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 간편인증)에 따라 실명인증 및 ③ 조회된 화면 하단 [수정] 버튼 클릭 → 항목 수정 후 [저장] 버튼 클릭
- E17 | rank=7 source=parent_section_expansion context_type=parent_section rrf=0.0300 dense=0.9163 bm25=3.1087 rerank=0.805608868598938 | p.15 / section / 섹션 11, p.15, 분할 0 / section_11_0
  - 11. 개명한 이름으로 변경하고 싶어요 ∎ 개인통관고유부호 발급 후 개명한 경우 PC 및 모바일을 이용하여 개인통관고유부호의 이름을 개명 후 이름으로 변경이 가능하며 방법은 다음과 같습니다. ※ 이름과 휴대전화번호가 변경된 경우는 [개명]버튼 활성화되지 않고 자동 개명 처리 ‣ 모바일 앱(App) 이용 시 ① [모바일관세청] 앱(App) 실행 후 [개인통관고유부호] 선택 ② 개명 후 성명과 주민등록번호 입력하여 선택한 본인인증 방법(휴대전화, 공동인증서, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회 ③ 발급내역 화면 이름 우측 [개명] 버튼 클릭하여 수정완료 ‣ 모바일 웹(Web) 이용 시 ① 포털사이트에서 ‘개인통관고유부호’ 검색하여 개인통관고유부호 사이트 진입 → [조회] 버튼 클릭 ② 개명 후 성명과 주민등록번호, 자동입력방지코드 입력하여 선택한 본인인증 방법(휴대폰인증, 간편인 증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회 ③ 발급내역 화면 이름 우측 [개명] 버튼 클릭하여 수정완료 ‣ PC 이용 시 ① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭 ② 개명 후 성명과 주민등록번호, 자동입력방지코드 입력하여 선택한 본인인증 방법(휴대폰인증, 공동/금 융인증서인증, 간편인증)에 따라 실명인증 및 본인인증
- E18 | rank=4 source=neighbor_expansion context_type=neighbor rrf=0.0303 dense=0.9152 bm25=3.8671 rerank=0.9245610237121582 | p.14 / text / 텍스트블록 29, 분할 0 / p14_text_b29_0
  - ③ 조회된 화면 하단 [수정] 버튼 클릭 → 항목 수정 후 [저장] 버튼 클릭
- E19 | rank=4 source=hybrid_rrf context_type=retrieved rrf=0.0303 dense=0.9152 bm25=3.8671 rerank=0.9245610237121582 | p.14 / text / 텍스트블록 30, 분할 0 / p14_text_b30_0
  - ‣ PC 이용 ① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭
- E20 | rank=5 source=neighbor_expansion context_type=neighbor rrf=0.0214 dense=0.9085 bm25=1.5899 rerank=0.9161800742149353 | p.14 / text / 텍스트블록 14, 분할 0 / p14_text_b14_0
  - ③ 조회된 화면 하단 [수정] 버튼 클릭→사용여부 ‘사용정지’ 또는 '재발급'을 선택 후 [저장] 버튼 클릭
- E21 | rank=5 source=hybrid_rrf context_type=retrieved rrf=0.0214 dense=0.9085 bm25=1.5899 rerank=0.9161800742149353 | p.14 / text / 텍스트블록 16, 분할 0 / p14_text_b16_0
  - ① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭
- E22 | rank=5 source=neighbor_expansion context_type=neighbor rrf=0.0214 dense=0.9085 bm25=1.5899 rerank=0.9161800742149353 | p.14 / text / 텍스트블록 17, 분할 0 / p14_text_b17_0
  - ② 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공동/금융인증서인증, 간편인
- E23 | rank=5 source=neighbor_expansion context_type=neighbor rrf=0.0214 dense=0.9085 bm25=1.5899 rerank=0.9161800742149353 | p.14 / text / 텍스트블록 18, 분할 0 / p14_text_b18_0
  - 증)에 따라 실명인증및 본인인증 후 개인통관고유부호 조회
- E24 | rank=7 source=neighbor_expansion context_type=neighbor rrf=0.0300 dense=0.9163 bm25=3.1087 rerank=0.805608868598938 | p.15 / text / 텍스트블록 12, 분할 0 / p15_text_b12_0
  - 증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회
- E25 | rank=7 source=hybrid_rrf context_type=retrieved rrf=0.0300 dense=0.9163 bm25=3.1087 rerank=0.805608868598938 | p.15 / text / 텍스트블록 14, 분할 0 / p15_text_b14_0
  - ‣ PC 이용 시 ① 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클릭 ② 개명 후 성명과 주민등록번호, 자동입력방지코드 입력하여 선택한 본인인증 방법(휴대폰인증, 공동/금
- E26 | rank=7 source=neighbor_expansion context_type=neighbor rrf=0.0300 dense=0.9163 bm25=3.1087 rerank=0.805608868598938 | p.15 / text / 텍스트블록 15, 분할 0 / p15_text_b15_0
  - 융인증서인증, 간편인증)에 따라 실명인증 및 본인인증 후 개인통관고유부호 조회
- E27 | rank=10 source=hybrid_rrf context_type=retrieved rrf=0.0206 dense=0.9056 bm25=1.5899 rerank=0.7165800929069519 | p.13 / text / 텍스트블록 21, 분할 0 / p13_text_b21_0
  - 개인통관고유부호 발급사이트(https://unipass.customs.go.kr/csp/persIndex.do) 접속 → [조회] 버튼 클
- E28 | rank=10 source=neighbor_expansion context_type=neighbor rrf=0.0206 dense=0.9056 bm25=1.5899 rerank=0.7165800929069519 | p.13 / text / 텍스트블록 22, 분할 0 / p13_text_b22_0
  - 릭 → 성명, 주민등록번호, 자동입력방지코드 입력하여 본인인증방법(휴대폰인증, 공인/금융인증서인
