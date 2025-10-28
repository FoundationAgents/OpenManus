// This file is auto-generated, don't edit it
import * as $dara from '@darabonba/typescript';


export class GetLabelRequest extends $dara.Model {
  authorization?: string;
  maxResults?: number;
  nextToken?: string;
  sessionId?: string;
  static names(): { [key: string]: string } {
    return {
      authorization: 'Authorization',
      maxResults: 'MaxResults',
      nextToken: 'NextToken',
      sessionId: 'SessionId',
    };
  }

  static types(): { [key: string]: any } {
    return {
      authorization: 'string',
      maxResults: 'number',
      nextToken: 'string',
      sessionId: 'string',
    };
  }

  validate() {
    super.validate();
  }

  constructor(map?: { [key: string]: any }) {
    super(map);
  }
}

