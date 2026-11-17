import assert from 'node:assert/strict';
import test from 'node:test';
import { formatRate } from '../utils/measurementPresentation.js';

test('rates display counts and missing denominators without implying a measured zero', () => {
  assert.equal(formatRate({numerator:0,denominator:0,value:null}), 'Not applicable (0/0)');
  assert.equal(formatRate({numerator:0,denominator:2,value:0}), '0.0% (0/2)');
  assert.equal(formatRate({numerator:1,denominator:3,value:1/3}), '33.3% (1/3)');
  assert.equal(formatRate(undefined), 'Not applicable');
});
