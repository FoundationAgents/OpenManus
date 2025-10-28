// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class ListSessionRequest extends $dara.Model {
  authorization?: string;
  labels?: string;
  maxResults?: number;
  nextToken?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      labels: 'Labels',
      maxResults: 'MaxResults',
      nextToken: 'NextToken',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      labels: 'string',
      maxResults: 'number',
      nextToken: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

