'''mermaid
flowchart TB
subgraph "Content Processing"
URL[Source URL] --> EXTRACT[Content Extraction]
EXTRACT --> ANALYZE[Topic Analysis]
end

    subgraph "Script Generation - Ollama"
        ANALYZE --> OUTLINE[Episode Outline]
        OUTLINE --> DIALOG[Dialog Generation]
        DIALOG --> SCRIPT[Structured Script JSON]
    end

    subgraph "Audio Synthesis - Polly"
        SCRIPT --> PARSE[Parse Speaker Turns]
        PARSE --> HOST1[Host 1: Matthew - Neural]
        PARSE --> HOST2[Host 2: Joanna - Neural]
        HOST1 --> MIX[Interleave Audio Segments]
        HOST2 --> MIX
        MIX --> S3[Store in S3]
    end

    subgraph "Delivery"
        S3 --> PLAYER[Audio Player]
        SCRIPT --> TRANSCRIPT[Timestamped Transcript]
    end

'''
