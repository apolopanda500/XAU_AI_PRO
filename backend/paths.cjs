const fs = require('fs');
const path = require('path');

function dataCandidates() {
  const candidates = [];
  if (process.env.XAU_AI_PRO_MQL_DATA) candidates.push(process.env.XAU_AI_PRO_MQL_DATA);
  candidates.push(path.resolve(__dirname, '..', '..', 'Data'));
  candidates.push(path.resolve(__dirname, '..', 'MQL5', 'Files', 'Data'));
  return candidates;
}

function resolveDataDir() {
  const candidates = dataCandidates();
  return candidates.find(candidate => fs.existsSync(candidate)) || candidates[0];
}

module.exports = { resolveDataDir };
