# AI Query Feature for Document Viewer

This feature allows users to submit queries about documents to DeepSeek v3.2 via OpenRouter API.

## Features

- 🔐 **Secure API Key Management**: Uses password-protected encrypted API key storage
- 💾 **Local Storage**: All queries and responses are stored in browser's IndexedDB
- 🔄 **Smart Caching**: Duplicate queries are loaded from cache instead of making new API calls
- 📊 **Metadata Tracking**: Tracks input/output tokens, duration, and cost for each query
- 🎯 **Document Context**: Automatically includes full document text with user queries
- 📜 **Query History**: View all past queries for each document in the agency card

## How It Works

### 1. API Key Encryption

The OpenRouter API key is encrypted using AES-256-CBC encryption and stored as a constant in the code:
```javascript
const ENCRYPTED_API_KEY = '65887f5d109435ade82c32bf64dabba3:3cfe3c769252ebd9373714781f8b283d:...'
```

To decrypt the API key, users need to provide a secret password. This happens in the browser using the Web Crypto API.

### 2. Query Submission

When a user submits a query:
1. The query is checked against IndexedDB for duplicates
2. If found, the cached result is displayed
3. If not found, the query is sent to DeepSeek v3.2 with the full document text
4. The response is stored in IndexedDB with metadata

### 3. Data Storage

All data is stored locally in the browser using IndexedDB:
- Database name: `MCYJ_Queries`
- Store name: `queries`
- Indexed by: `sha256`, `queryHash`, `timestamp`

Each query record contains:
- `sha256`: Document identifier
- `query`: User's question
- `queryHash`: Hash of query for quick lookups
- `response`: AI's response
- `inputTokens`: Number of input tokens
- `outputTokens`: Number of output tokens
- `cost`: API cost (if provided)
- `durationMs`: Query processing time
- `timestamp`: When the query was made

## Usage

### In the Document Viewer

1. Open a document by clicking "View Full Document"
2. In the document modal, find the "Ask AI About This Document" section
3. Enter the secret password and click "Unlock"
4. Type your question in the text area
5. Click "Submit Query"
6. Wait for the response (spinner will show)
7. View the response and query history below

### Query History in Agency Cards

Each document in the agency card shows:
- Number of AI queries saved for that document
- Clicking "View Full Document" shows the full query history

## API Details

### OpenRouter Configuration

- **Endpoint**: `https://openrouter.ai/api/v1/chat/completions`
- **Model**: `deepseek/deepseek-chat` (DeepSeek v3.2)
- **Prompt Format**: `{user_query}\n\n{document_text}`

### Request Headers

```javascript
{
  'Authorization': `Bearer ${apiKey}`,
  'Content-Type': 'application/json',
  'HTTP-Referer': window.location.href,
  'X-Title': 'MCYJ Datapipeline Document Viewer'
}
```

## Security Considerations

1. **No Secrets in Code**: The actual API key is never stored in the code, only an encrypted version
2. **Client-Side Decryption**: Decryption happens entirely in the browser
3. **Local Storage Only**: All queries and responses stay in the user's browser
4. **No Server Logging**: Queries are sent directly from browser to OpenRouter API

## Development

### Testing Locally

For local testing, you can:
1. Use the repository secret `OPENROUTER_KEY` (available in GitHub Actions)
2. Create a test password and encrypt your own API key
3. Use the `test.html` page to verify functionality

### File Structure

```
website/src/
├── main.js           # Main application with AI query UI integration
├── indexedDB.js      # IndexedDB operations for query storage
├── encryption.js     # API key decryption utilities
└── apiService.js     # OpenRouter API integration
```

## Future Enhancements

Potential improvements:
- Support for multiple AI models
- Export query history
- Query templates for common questions
- Batch querying multiple documents
- Query result sharing (with privacy controls)

## Troubleshooting

### "Invalid password" error
- Verify you're using the correct secret password
- The password is case-sensitive

### Query not appearing in history
- Check browser console for IndexedDB errors
- Verify IndexedDB is enabled in browser settings

### API errors
- Check browser console for detailed error messages
- Verify OpenRouter API key is valid and has credits
- Check network connectivity

## License

Part of the Michigan Child Welfare Licensing Dashboard project.
